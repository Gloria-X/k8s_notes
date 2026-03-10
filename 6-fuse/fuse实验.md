存储后端： Ceph RGW（提供s3兼容接口）

访问方式：Goofys（一个fuse文件系统） --> 把s3挂载成/data

k8s集成：通过meta-fuse-csi-plugin CSI驱动实现安全挂载

> 它用的是 Ceph 的对象存储能力，但通过 FUSE 方式暴露为文件系统

| 对比项       | FUSE + S3（如 Goofys）                                     | 原生 Ceph（CephFS / RBD）                                 |
| ------------ | ---------------------------------------------------------- | --------------------------------------------------------- |
| 存储类型     | 对象存储（S3）                                             | 文件存储（CephFS）或块存储（RBD）                         |
| 协议         | HTTP/REST（S3 API）                                        | Ceph 原生协议（ librados / kernel client）                |
| POSIX 兼容性 | ❌ 不完全兼容（如不支持 hard link、mmap 等）                | ✅ 完全兼容（尤其是 CephFS）                               |
| 性能         | ⚠️ 中等，受网络和 S3 语义限制 （你测得 ~254 MB/s 已算很好） | ✅ 高性能，低延迟，适合高 IOPS 场景                        |
| 跨集群迁移性 | ✅ 极强！只要能访问 S3 endpoint，任何集群都能挂载           | ❌ 弱！CephFS/RBD 绑定到特定 Ceph 集群，IP/网络/认证都耦合 |
| 权限模型     | 基于 bucket + IAM（AccessKey）                             | 基于 Ceph 用户 + caps（cephx）                            |
| 典型用途     | AI 数据集、日志、媒体文件、备份                            | 数据库、虚拟机磁盘、高性能计算                            |





为什么 meta-fuse-csi-plugin 用的是 Ephemeral？

- s3 bucket 本身已经持久化了（数据在 Ceph RGW 里），不需要k8s再管理“持久卷”
- 每个pod只需要 临时挂载 这个 bucket 到本地路径
- 不同pod挂同一个 bucket 是各自独立挂载，不是共享同一个 PV
- 所以它用 Ephemeral 模式：K8s 不管理存储生命周期，只负责“挂载动作”

CephFS/RBD：

- k8s 需要为每个 PVC 分配一块独立的存储空间（比如 10GiB 的 CephFS 目录）
- 这块空间要跟踪谁在用、能不能删、配额多少……所以必须用 Persistent



#### FUSE的真实模式

fuse不是“配置”，而是一个正在运行的进程

```
goofys  ← 一个用户态进程
  |
  | 通过 /dev/fuse
  ↓
Linux VFS
  |
  ↓
/mnt  ← 你看到的目录
```

/mnt 不是“被挂载好的”，而是「goofys 这个进程挂出来的」

所以/mnt一开始是个普通空目录，只有当goofys bucket /mnt这个进程运行成功，/mnt才会变成s3视图



goofys只能接收两个位置参数

```
goofys  <bucket>  <mountpoint>
```





### 环境

#### 安装meta-fuse-csi-plugin

克隆官方仓库

```
git clone https://github.com/pfnet-research/meta-fuse-csi-plugin.git
cd meta-fuse-csi-plugin
```

应用CSI驱动定义和RBAC

```
kubectl apply -f deploy/csi-driver.yaml
```

包括namespace, serviceAccount, clusterRole, CSIDriver

应用DaemonSet

```
kubectl apply -f deploy/csi-driver-daemonset.yaml
```

验证是否安装了CSI Driver

> k8s版的sshfs

```
jcjy@jcjy-msi:~$ kubectl get csidriver
NAME                                      ATTACHREQUIRED   PODINFOONMOUNT   STORAGECAPACITY   TOKENREQUESTS   REQUIRESREPUBLISH   MODES        AGE
meta-fuse-csi-plugin.csi.storage.pfn.io   false            true             false             <unset>         true                Ephemeral    28s
...
```

验证插件pod在运行

```
jcjy@jcjy-msi:~$ kubectl get pods -A | grep meta-fuse
mfcp-system          meta-fuse-csi-plugin-dqjzf                                  2/2     Running     0              47s
```



#### 本地有docker minio

```
ssh -p 46811 -L 0.0.0.0:9003:192.168.1.150:9001 rens@jcjy.synology.me
```



docker inspect中可查看

- 用户名: admin
- 密码: adminpassw0rd



创建pod后报错

```
Events:
  Type     Reason          Age               From               Message
  ----     ------          ----              ----               -------
  Normal   Scheduled       25s               default-scheduler  Successfully assigned default/minio-test-pod to jcjy-msi
  Normal   AddedInterface  24s               multus             Add eth0 [10.244.0.120/24] from cbr0
  Normal   Pulled          24s               kubelet            Container image "ghcr.io/pfnet-research/meta-fuse-csi-plugin/mfcp-example-proxy-goofys:latest" already present on machine
  Normal   Created         24s               kubelet            Created container starter
  Normal   Started         24s               kubelet            Started container starter
  Warning  Failed          21s               kubelet            Error: failed to generate container "ab9eff67f549bb8b64a738d8cb12df4a7ac37a10609e96845c2429843f6a8c21" spec: failed to generate spec: failed to stat "/var/lib/kubelet/pods/c11a77ea-4ec8-4190-ae5b-19d631bf9121/volumes/kubernetes.io~csi/fuse-csi-ephemeral/mount": stat /var/lib/kubelet/pods/c11a77ea-4ec8-4190-ae5b-19d631bf9121/volumes/kubernetes.io~csi/fuse-csi-ephemeral/mount: transport endpoint is not connected
  Normal   Pulled          7s (x2 over 21s)  kubelet            Container image "ubuntu:22.04" already present on machine
  Warning  Failed          7s                kubelet            Error: failed to generate container "efdbc47e0c7d928f0a315076eb5cda0fe68d7d61ef07c22eaa0b6933a6172c37" spec: failed to generate spec: failed to stat "/var/lib/kubelet/pods/c11a77ea-4ec8-4190-ae5b-19d631bf9121/volumes/kubernetes.io~csi/fuse-csi-ephemeral/mount": stat /var/lib/kubelet/pods/c11a77ea-4ec8-4190-ae5b-19d631bf9121/volumes/kubernetes.io~csi/fuse-csi-ephemeral/mount: transport endpoint is not connected
```

FUSE 挂载失败后残留挂载点导致的问题

本地下载goofys测试

[Release v0.24.0 - mo virus mo problems · kahing/goofys](https://github.com/kahing/goofys/releases/tag/v0.24.0)

```
chmod +x goofys

sudo mv goofys /usr/local/bin/

goofys --version
```

运行挂载语句

```
goofys --endpoint http://192.168.1.150:9000 --use-path-request-style --region us-east-1 fuse-test /mnt
```



再调整arg和comment，最终如下

```
apiVersion: v1
kind: Pod
metadata:
  name: minio-test-pod
  namespace: default
spec:
  terminationGracePeriodSeconds: 10

  containers:
    - name: goofys
      image: ghcr.io/pfnet-research/meta-fuse-csi-plugin/mfcp-example-proxy-goofys:latest
      imagePullPolicy: IfNotPresent
      securityContext:
        privileged: true
      command: ["/bin/bash"]
      args:
        - -c
        - |
          echo "Starting goofys..."
          export AWS_ACCESS_KEY_ID=admin
          export AWS_SECRET_ACCESS_KEY=adminpassw0rd
          exec /goofys \
            --endpoint http://192.168.1.150:9000 \
            --region us-east-1 \
            --stat-cache-ttl 0 \
            --type-cache-ttl 0 \
            -f \
            fuse-test /mnt 2>&1
      env:
        - name: FUSERMOUNT3PROXY_FDPASSING_SOCKPATH
          value: "/fusermount3-proxy/fuse-csi-ephemeral.sock"
        - name: AWS_ACCESS_KEY_ID
          value: "admin"
        - name: AWS_SECRET_ACCESS_KEY
          value: "adminpassw0rd"
      volumeMounts:
        - name: fuse-fd-passing
          mountPath: /fusermount3-proxy
        - name: fuse-csi-ephemeral
          mountPath: /mnt
          mountPropagation: Bidirectional

    - name: app
      image: ubuntu:22.04
      command: ["sleep", "infinity"]
      volumeMounts:
          - name: fuse-csi-ephemeral
            mountPath: /data
            mountPropagation: HostToContainer

  volumes:
    - name: fuse-fd-passing
      emptyDir: {}

    - name: fuse-csi-ephemeral
      csi:
        driver: meta-fuse-csi-plugin.csi.storage.pfn.io
        volumeAttributes:
          fdPassingEmptyDirName: fuse-fd-passing
          fdPassingSocketName: fuse-csi-ephemeral.sock

# kubectl apply -f minio-pod.yaml
# kubectl get pod minio-test-pod

# kubectl exec -it minio-test-pod -- ls /data
# kubectl exec -it minio-test-pod -- echo "Hello from Pod!" > /data/pod-test.txt

```

`--stat-cache-ttl 0` 意味着完全不缓存，这很安全（数据一致性高），但频繁 `ls` 会让minio压力很大

成功！

```
jcjy@jcjy-msi:~/xsy-project/fuse$ kubectl apply -f minio-pod.yaml
pod/minio-test-pod created
jcjy@jcjy-msi:~/xsy-project/fuse$ kubectl get pod minio-test-pod
NAME             READY   STATUS    RESTARTS   AGE
minio-test-pod   2/2     Running   0          8s
jcjy@jcjy-msi:~/xsy-project/fuse$ kubectl exec -it minio-test-pod -c app -- ls -lh /data
total 0
jcjy@jcjy-msi:~/xsy-project/fuse$ kubectl exec -it minio-test-pod -c app -- bash
root@minio-test-pod:/# echo "Hello MinIO from Pod at $(date)" > /data/pod-test.txt
root@minio-test-pod:/# ls -lh /data
total 512
-rw-r--r-- 1 root root 53 Feb  9 06:55 pod-test.txt
root@minio-test-pod:/# 
```



#### 压测

```
$ apt-get update && apt-get install -y fio

$ fio --name=fuse_test --directory=/data --rw=rw --bs=64k --size=1G --numjobs=4 --time_based --runtime=60 --group_reporting
```

观察

```
kubectl top pod minio-test-pod --containers
```



##### 单线程只读

先跑一次理想状态下的读取速度

```
fio --name=fuse_test --directory=/data --rw=read --bs=64k --size=1G --numjobs=1 --time_based --runtime=60 --group_reporting
```

实际结果

```
root@minio-test-pod:/# fio --name=fuse_test --directory=/data --rw=read --bs=64k --size=1G --numjobs=1 --time_based --runtime=60 --group_reporting
fuse_test: (g=0): rw=read, bs=(R) 64.0KiB-64.0KiB, (W) 64.0KiB-64.0KiB, (T) 64.0KiB-64.0KiB, ioengine=psync, iodepth=1
fio-3.28
Starting 1 process
fuse_test: Laying out IO file (1 file / 1024MiB)
Jobs: 1 (f=1): [R(1)][100.0%][r=1212MiB/s][r=19.4k IOPS][eta 00m:00s]
fuse_test: (groupid=0, jobs=1): err= 0: pid=703: Mon Feb  9 08:42:40 2026
  read: IOPS=21.0k, BW=1314MiB/s (1378MB/s)(77.0GiB/60000msec)
    clat (nsec): min=1814, max=233804k, avg=44744.92, stdev=237859.03
     lat (nsec): min=1830, max=233804k, avg=44780.49, stdev=237858.12
    clat percentiles (usec):
     |  1.00th=[    3],  5.00th=[    3], 10.00th=[    3], 20.00th=[    3],
     | 30.00th=[    4], 40.00th=[    4], 50.00th=[    4], 60.00th=[    5],
     | 70.00th=[    7], 80.00th=[  116], 90.00th=[  153], 95.00th=[  192],
     | 99.00th=[  322], 99.50th=[  396], 99.90th=[  603], 99.95th=[  758],
     | 99.99th=[ 2278]
   bw (  MiB/s): min=  657, max= 1630, per=100.00%, avg=1315.69, stdev=132.25, samples=119
   iops        : min=10516, max=26084, avg=21051.01, stdev=2116.09, samples=119
  lat (usec)   : 2=0.03%, 4=53.04%, 10=20.88%, 20=0.94%, 50=0.09%
  lat (usec)   : 100=1.03%, 250=21.75%, 500=2.04%, 750=0.15%, 1000=0.02%
  lat (msec)   : 2=0.02%, 4=0.01%, 10=0.01%, 20=0.01%, 50=0.01%
  lat (msec)   : 250=0.01%
  cpu          : usr=1.02%, sys=38.42%, ctx=633755, majf=0, minf=31
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=1261665,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=1314MiB/s (1378MB/s), 1314MiB/s-1314MiB/s (1378MB/s-1378MB/s), io=77.0GiB (82.7GB), run=60000-60000msec
```

资源消耗

```
jcjy@jcjy-msi:~$ kubectl top pod minio-test-pod --containers
POD              NAME     CPU(cores)   MEMORY(bytes)
minio-test-pod   app      365m         87Mi
minio-test-pod   goofys   648m         664Mi
```



##### 多线程读写

```
fio --name=fuse_test --directory=/data --rw=rw --bs=64k --size=1G --numjobs=4 --time_based --runtime=60 --group_reporting
```

实际结果

```
root@minio-test-pod:/# fio --name=fuse_test --directory=/data --rw=rw --bs=64k --size=1G --numjobs=4 --time_based --runtime=60 --group_reporting
fuse_test: (g=0): rw=rw, bs=(R) 64.0KiB-64.0KiB, (W) 64.0KiB-64.0KiB, (T) 64.0KiB-64.0KiB, ioengine=psync, iodepth=1
...
fio-3.28
Starting 4 processes
fuse_test: Laying out IO file (1 file / 1024MiB)
fuse_test: Laying out IO file (1 file / 1024MiB)
fuse_test: Laying out IO file (1 file / 1024MiB)
fio: pid=0, err=5/file:filesetup.c:240, func=write, error=Input/output error
fio: pid=716, err=5/file:backend.c:479, func=full resid, error=Input/output error
fio: pid=714, err=5/file:backend.c:479, func=full resid, error=Input/output error
fio: io_u error on file /data/fuse_test.3.0: Operation not supported: write offset=0, buflen=65536
fio: pid=715, err=95/file:io_u.c:1845, func=io_u error, error=Operation not supported
Jobs: 1 (f=1): [f(1),X(3)][-.-%][r=555MiB/s,w=559MiB/s][r=8873,w=8945 IOPS][eta 00Jobs: 1 (f=1): [f(1),X(3)][-.-%][eta 00m:00s]                                     Jobs: 1 (f=1): [f(1),X(3)][-.-%][eta 00m:00s]
fuse_test: (groupid=0, jobs=4): err= 5 (file:backend.c:479, func=full resid, error=Input/output error): pid=714: Mon Feb  9 08:46:07 2026
  read: IOPS=8764, BW=548MiB/s (574MB/s)(1012MiB/1848msec)
    clat (usec): min=3, max=7731, avg= 8.08, stdev=82.83
     lat (usec): min=3, max=7732, avg= 8.12, stdev=82.84
    clat percentiles (usec):
     |  1.00th=[    5],  5.00th=[    5], 10.00th=[    6], 20.00th=[    6],
     | 30.00th=[    6], 40.00th=[    6], 50.00th=[    7], 60.00th=[    7],
     | 70.00th=[    7], 80.00th=[    8], 90.00th=[    9], 95.00th=[   11],
     | 99.00th=[   19], 99.50th=[   28], 99.90th=[   74], 99.95th=[  379],
     | 99.99th=[ 6915]
   bw (  KiB/s): min=496171, max=623583, per=100.00%, avg=566103.00, stdev=64611.62, samples=3
   iops        : min= 7751, max= 9743, avg=8844.67, stdev=1009.63, samples=3
  write: IOPS=8876, BW=555MiB/s (582MB/s)(1025MiB/1848msec); 0 zone resets
    clat (usec): min=29, max=48414, avg=100.49, stdev=697.10
     lat (usec): min=29, max=48414, avg=100.85, stdev=697.13
    clat percentiles (usec):
     |  1.00th=[   34],  5.00th=[   36], 10.00th=[   37], 20.00th=[   39],
     | 30.00th=[   41], 40.00th=[   43], 50.00th=[   46], 60.00th=[   49],
     | 70.00th=[   52], 80.00th=[   58], 90.00th=[   80], 95.00th=[  143],
     | 99.00th=[  979], 99.50th=[ 2376], 99.90th=[ 7963], 99.95th=[12649],
     | 99.99th=[30540]
   bw (  KiB/s): min=515046, max=616400, per=100.00%, avg=573066.33, stdev=52248.06, samples=3
   iops        : min= 8046, max= 9631, avg=8953.67, stdev=816.52, samples=3
  lat (usec)   : 4=0.15%, 10=46.59%, 20=2.54%, 50=32.56%, 100=14.40%
  lat (usec)   : 250=2.16%, 500=0.79%, 750=0.19%, 1000=0.12%
  lat (msec)   : 2=0.21%, 4=0.15%, 10=0.11%, 20=0.03%, 50=0.01%
  cpu          : usr=1.59%, sys=25.09%, ctx=33172, majf=0, minf=72
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.1%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=16197,16404,0,0 short=0,0,0,0 dropped=0,0,0,0

Run status group 0 (all jobs):
   READ: bw=548MiB/s (574MB/s), 548MiB/s-548MiB/s (574MB/s-574MB/s), io=1012MiB (1061MB), run=1848-1848msec
  WRITE: bw=555MiB/s (582MB/s), 555MiB/s-555MiB/s (582MB/s-582MB/s), io=1025MiB (1075MB), run=1848-1848msec
```

资源消耗

```
jcjy@jcjy-msi:~$ kubectl top pod minio-test-pod --containers
POD              NAME     CPU(cores)   MEMORY(bytes)
minio-test-pod   app      3m           92Mi
minio-test-pod   goofys   1m           671Mi
```

崩溃了，--rw=rw（混合随机读写）时，fio默认会尝试在文件的不同offset进行写入

s3的限制：不能像在本地硬盘上那样，打开一个文件，然后修改其中间的某个字节，要么创建新的文件，要么覆盖

goofys：为了性能，对随机写的支持非常有限，当fio尝试在同一个文件上进行复杂的读写交替操作时，goofys无法向s3解释这种”修改中间某段“的行为，直接抛出Operation not supported，导致fio认为磁盘损坏，触发Input/output error



##### 混合压测

模拟大模型场景，一边读数据，一边存checkpoint

```
fio --name=sequential_test --directory=/data --rw=readwrite --bs=128k --size=1G --numjobs=2 --group_reporting
```

实际结果

```
root@minio-test-pod:/# fio --name=sequential_test --directory=/data --rw=readwrite --bs=128k --size=1G --numjobs=2 --group_reporting
sequential_test: (g=0): rw=rw, bs=(R) 128KiB-128KiB, (W) 128KiB-128KiB, (T) 128KiB-128KiB, ioengine=psync, iodepth=1
...
fio-3.28
Starting 2 processes
sequential_test: Laying out IO file (1 file / 1024MiB)
sequential_test: Laying out IO file (1 file / 1024MiB)
fio: pid=727, err=5/file:backend.c:479, func=full resid, error=Input/output error
Jobs: 2 (f=2): [f(2)][-.-%][r=27.5MiB/s,w=31.1MiB/s][r=220,w=249 IOPS][eta 00m:00sJobs: 2 (f=2): [f(2)][-.-%][eta 00m:00s]                                          Jobs: 2 (f=2): [f(2)][-.-%][eta 00m:00s]
sequential_test: (groupid=0, jobs=2): err= 5 (file:backend.c:479, func=full resid, error=Input/output error): pid=727: Mon Feb  9 08:53:50 2026
  read: IOPS=4379, BW=547MiB/s (574MB/s)(504MiB/920msec)
    clat (usec): min=8, max=16966, avg=24.55, stdev=342.24
     lat (usec): min=8, max=16967, avg=24.60, stdev=342.28
    clat percentiles (usec):
     |  1.00th=[   10],  5.00th=[   11], 10.00th=[   11], 20.00th=[   12],
     | 30.00th=[   13], 40.00th=[   13], 50.00th=[   14], 60.00th=[   15],
     | 70.00th=[   16], 80.00th=[   18], 90.00th=[   21], 95.00th=[   27],
     | 99.00th=[   47], 99.50th=[   57], 99.90th=[  594], 99.95th=[ 8455],
     | 99.99th=[16909]
   bw (  KiB/s): min=489983, max=489984, per=87.43%, avg=489984.00, stdev= 0.00, samples=1
   iops        : min= 3827, max= 3828, avg=3828.00, stdev= 0.00, samples=1
  write: IOPS=4538, BW=567MiB/s (595MB/s)(522MiB/920msec); 0 zone resets
    clat (usec): min=46, max=11517, avg=200.32, stdev=696.31
     lat (usec): min=47, max=11518, avg=201.27, stdev=696.49
    clat percentiles (usec):
     |  1.00th=[   53],  5.00th=[   59], 10.00th=[   62], 20.00th=[   67],
     | 30.00th=[   71], 40.00th=[   74], 50.00th=[   78], 60.00th=[   83],
     | 70.00th=[   92], 80.00th=[  109], 90.00th=[  200], 95.00th=[  429],
     | 99.00th=[ 3556], 99.50th=[ 5538], 99.90th=[ 8586], 99.95th=[11207],
     | 99.99th=[11469]
   bw (  KiB/s): min=511743, max=511744, per=88.10%, avg=511744.00, stdev= 0.00, samples=1
   iops        : min= 3997, max= 3998, avg=3998.00, stdev= 0.00, samples=1
  lat (usec)   : 10=2.49%, 20=41.21%, 50=5.19%, 100=39.09%, 250=7.33%
  lat (usec)   : 500=2.33%, 750=0.57%, 1000=0.30%
  lat (msec)   : 2=0.55%, 4=0.45%, 10=0.41%, 20=0.06%
  cpu          : usr=1.78%, sys=22.15%, ctx=8574, majf=0, minf=41
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.1%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=4029,4175,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=547MiB/s (574MB/s), 547MiB/s-547MiB/s (574MB/s-574MB/s), io=504MiB (528MB), run=920-920msec
  WRITE: bw=567MiB/s (595MB/s), 567MiB/s-567MiB/s (595MB/s-595MB/s), io=522MiB (547MB), run=920-920msec
```

资源消耗

```
jcjy@jcjy-msi:~$ kubectl top pod minio-test-pod --containers
POD              NAME     CPU(cores)   MEMORY(bytes)
minio-test-pod   app      0m           84Mi
minio-test-pod   goofys   994m         45Mi
```

还是崩溃，因为readwrite模式是在同一个测试文件上交替进行读写操作，goofys无法处理对同一个文件的并发读写冲突

为了保证性能，goofys采用的是一种“全量上传”模式。在文件关闭（close）之前，数据往往存在本地缓存或分段中。如果你在它还没写完（上传成功）时就尝试复杂的混合操作，goofys会因为无法维持 POSIX 强一致性而直接向内核报错



##### 流式写入

```
root@minio-test-pod:/# time dd if=/dev/urandom of=/data/checkpoints/model.bin bs=1M count=500
500+0 records in
500+0 records out
524288000 bytes (524 MB, 500 MiB) copied, 1.46994 s, 357 MB/s

real    0m1.484s
user    0m0.005s
sys     0m1.239s
```



###### 为什么 dd 成功了而 fio 失败了？

dd 的逻辑：打开新文件 -> 顺着写到底 -> 关闭，这在 S3 看来是一个标准的 PUT 请求

fio 的逻辑：打开文件 -> 预分配空间（fallocate） -> 随机跳着写，这在 S3 看来是“非法修改”，所以报错











---

### 把init container改为sidecar container

| **特性**        | **Init Container 方案 (原来的)**                             | **Sidecar Container 方案 (现在的)**                          |
| --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **生命周期**    | 在应用容器启动**前**运行并退出。                             | 与应用容器**同时**运行，伴随始终。                           |
| **稳定性**      | **致命缺陷**：如果 FUSE 进程在应用运行期间崩溃，没有人会重启它。 | **自动恢复**：如果 Sidecar 崩溃，Kubernetes 会自动重启它，重新挂载。 |
| **FD 传递机制** | 依赖特定的 `restartPolicy: Always`（K8s 1.29+ 新特性）或单次传递。 | 能够持续维持 Unix Domain Socket 的连接和文件描述符传递。     |
| **挂载点表现**  | 容易出现 `Transport endpoint is not connected` 且无法自愈。  | 进程重启后，通过 Mount Propagation 能够尝试恢复挂载。        |

在 K8s 中，普通的 Init Container 必须执行完并退出，主容器才会启动。但 FUSE 进程（goofys）必须一直活着才能维持挂载。

- 如果你把 goofys 放在普通的 Init Container 里且它不退出，主容器永远起不来
- 如果你让 goofys 后台运行然后 Init Container 退出，由于容器空间隔离，Init 容器退出后它启动的后台进程往往会被清理掉，导致主容器看到的是一个死掉的挂载点

Meta FUSE CSI 改为 Sidecar 模式

- 解耦与容错：Sidecar 模式下，goofys 是一个独立的进程。如果 S3 网络波动导致 goofys 卡死或崩溃，Kubernetes 的探针（Liveness Probe）可以检测到并只重启 goofys 容器，而不必重启你的业务 app 容器

- 挂载传播 (Mount Propagation)
  - goofys 容器设置为 Bidirectional（双向）：它把 FUSE 内容挂载到宿主机目录
  - app 容器设置为 HostToContainer（宿主机到容器）：它从宿主机获取这个动态更新的内容。 这样，Sidecar 就像一个后台服务，源源不断地把 S3 数据“泵”到 app 容器里







































