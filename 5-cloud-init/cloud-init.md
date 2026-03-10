# cloud init

[Chapter 2. Introduction to cloud-init | Configuring and managing cloud-init for RHEL 9 | Red Hat Enterprise Linux | 9 | Red Hat Documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_cloud-init_for_rhel_9/introduction-to-cloud-init_cloud-content?spm=5176.28103460.0.0.b2e87551Re0iiM)

cloud-init 工具能在系统启动期间，自动完成云实例的初始化工作

是“开机时自动运行”的，不需要你手动登录去配置

可以配置 cloud-init 来执行多种任务

- 配置主机名

​	默认云镜像的主机名可能是 ubuntu 或随机名，可以通过 cloud-init 把它改成 web-server-01、db-prod...

- 在实例上安装软件包

​	自动安装nginx, pip, docker.io...

- 运行脚本

  可以执行自定义的 shell 脚本、python 脚本等，支持设置“启动时只运行一次”或“每次启动都运行”

- 抑制（关闭）虚拟机的默认行为

  比如：Ubuntu cloud 镜像默认会自动扩容磁盘、生成 SSH 密钥、设置 locale 等，如果不希望某些默认行为发生，可以用 cloud-init 禁用它们

## 概念

### 前提条件 Prerequisites

要使用 cloud-init 配置 RHEL 虚拟机，需要先满足...

- 注册一个 Red Hat 客户门户网站账户[Red Hat Customer Portal - Access to 24x7 support and knowledge](https://access.redhat.com/?spm=5176.28103460.0.0.b2e87551qA0iBU)

```
Gloria_X
XSY2001.05.30wabm
```

cloud-init 可用于多种类型的 RHEL 镜像

- 如果是从 Red Hat 客户门户下载的是 KVM 客户机镜像，该镜像已经预装了 cloud-init 包；启动实例后，cloud-init 会自动启用

- 从Red Hat 客户门户下载 RHEL ISO 镜像，用来制作自定义的客户机镜像，需要手动在自定义镜像中安装 cloud-init 软件包

  ISO 安装的是“传统服务器系统”，默认不包含 cloud-init

  如果你想把这个自定义镜像用于云环境（比如批量部署 VM），就需要自己装

  ```
  sudo dnf install cloud-init
  ```

  还要清理机器 ID、SSH 密钥等，否则克隆出来的 VM 会有冲突

- 使用云服务商（AWS/Azure 等）或 RHEL Image Builder

  Image Builder 生成的镜像已针对特定云平台定制，并且已预装 cloud-init



### cloud-init configuration

yaml来配置

当实例启动时，cloud-init 服务会启动，并执行 YAML 文件中的指令。根据配置不同，这些任务可能在首次启动时执行，也可能在后续启动时执行

有些模块（比如 runcmd 默认只跑一次，但你可以用 bootcmd 或 power_state 等实现每次启动都运行）

cloud-init 会记录状态到 /var/lib/cloud/instance/，避免重复执行

要定义具体任务，可以配置 /etc/cloud/cloud.cfg 文件，并在 /etc/cloud/cloud.cfg.d/ 目录下添加配置指令

> 这是系统级配置（镜像制作者或者管理员使用）
>
> 和之前看到的用户提供的user-data不同
>
> - user-data：由用户在启动时提供，用于定制单个实例
> - cloud.cfg：是镜像内部的全局配置，控制 cloud-init 如何工作（比如启用哪些模块）
>
> 除非自己制作基础镜像，否则通常不需要改cloud.cfg

cloud.cfg 文件包含各种系统配置指令，例如用户访问、认证和系统信息

```
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAA... user@host
disable_root: true
ssh_pwauth: false
```

该文件还包含 cloud-init 的默认和可选模块。这些模块按顺序在以下三个阶段执行

1. 初始化阶段（initialization）
2. 配置阶段（configuration）
3. 最终阶段（final）

在 cloud.cfg 中，这三个阶段的模块分别列在：

- cloud_init_modules
- cloud_config_modules
- cloud_final_modules

| 阶段   | 时机                           | 典型模块                                                     | 用途                           |
| ------ | ------------------------------ | ------------------------------------------------------------ | ------------------------------ |
| init   | 系统早期启动（网络可能还没通） | `migrator`, `seed_random`, `bootcmd`                         | 准备环境、执行早期命令         |
| config | 网络已就绪，用户空间基本可用   | `set_hostname`, `update_etc_hosts`, `package_update`, `packages`, `users-groups` | 核心配置：主机名、用户、装包等 |
| final  | 所有服务基本启动完成           | `scripts-user`, `phone_home`, `power_state`                  | 运行用户脚本、关机、上报状态等 |

可以在 cloud.cfg.d/ 目录中为 cloud-init 添加额外的配置指令。添加时，需将指令写入一个以 .cfg 结尾的自定义文件中，并且文件顶部必须包含 #cloud-config

❗ #cloud-config 只用于 user-data 文件！

而 /etc/cloud/cloud.cfg.d/*.cfg 是 系统配置片段，不需要也不应该加 #cloud-config







## 流程

```mermaid
graph LR
A[已有 ubuntu-24.04.qcow2] --> B[编写 user-data 和 meta-data]
B --> C[用 cloud-localds 生成 cidata.iso]
C --> D[用 qemu-system-x86_64 启动 VM 并挂载 ISO]
D --> E[VM 首次启动，cloud-init 自动应用配置]
E --> F[验证：主机名、软件是否安装成功]
```



### KubeVirt 处理 cloudInitNoCloud.userData

当在vm yaml中写

```
volumes:
  - name: cloudinitdisk
    cloudInitNoCloud:
      userData: |
        #cloud-config
        hostname: my-vm
        users:
          - name: ubuntu
```

KubeVirt 会在 VM 启动时

1. 自动创建一个 虚拟 CD-ROM
2. 把写的 userData 内容 原样写入 CD-ROM 中的 user-data 文件
3. 把空的或简单的 meta-data 也放进去

所以 VM 内部看到的 /dev/cdrom 挂载后是

```
/media/cidata/
├── user-data   ← 就是你写的全部内容（包括 #cloud-config）
└── meta-data
```







## qemu实验

### qemu配置cloud-init

windows 镜像（如 win10.qcow2）不支持 cloud-init —— cloud-init 是 Linux 专用 的初始化工具（主要用在 Ubuntu、RHEL、CentOS 等发行版上）

下载Ubuntu 24.04 (Noble) 云镜像

```
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img -O ubuntu-24.04.qcow2
```

确认镜像格式

```
jcjy@jcjy-msi:~/xsy-project/cloud-init$ qemu-img info ubuntu-24.04.qcow2
image: ubuntu-24.04.qcow2
file format: qcow2
virtual size: 3.5 GiB (3758096384 bytes)
disk size: 598 MiB
cluster_size: 65536
Format specific information:
    compat: 1.1
    compression type: zlib
    lazy refcounts: false
    refcount bits: 16
    corrupt: false
    extended l2: false
```

格式已经是qcow2，而非raw，不用特意扩容

这个镜像已经预装 cloud-init，默认用户是 `ubuntu`



### 准备cloud-init配置（NoCloud方式）

创建三个文件

```
# user-data：设置密码 + 允许 SSH 密码登录（方便测试）
cat > user-data << 'EOF'
#cloud-config
password: mypassword
chpasswd: { expire: False }
ssh_pwauth: True   # 允许密码 SSH 登录
package_upgrade: true
packages:
  - nginx
runcmd:
  - systemctl start nginx
  - echo "Welcome from cloud-init!" > /var/www/html/index.html
EOF

# meta-data：必须提供 instance-id
cat > meta-data << EOF
instance-id: iid-local01
local-hostname: cloudinit-vm
EOF

# vendor-data（留空）
touch vendor-data
```



### 生成seed.iso

🌟QEMU 支持通过 虚拟 CD-ROM 挂载 ISO 来传递 cloud-init 配置（NoCloud 数据源）

这样不需要开 HTTP 服务器，也避免网络配置问题！

安装工具

```
sudo apt install cloud-image-utils
```

生成 ISO

```
cloud-localds seed.iso user-data meta-data
```



### 启动qemu（挂载cloud-init配置ISO）

```
sudo qemu-system-x86_64 \
  -enable-kvm \
  -m 2048 \
  -smp 2 \
  -drive file=ubuntu-24.04.qcow2,format=qcow2 \
  -cdrom seed.iso \
  -net nic -net user,hostfwd=tcp::2222-:22 \
  -nographic
```

- `-cdrom seed.iso`：cloud-init 会自动从 CD-ROM 读取 NoCloud 配置
- `-net user,hostfwd=tcp::2222-:22`：把 VM 的 22 端口映射到本机 2222，方便 SSH
- `-nographic`：日志直接打到终端（适合调试）

```
...
-----END SSH HOST KEY KEYS-----
[  166.440091] cloud-init[972]: Cloud-init v. 25.2-0ubuntu1~24.04.1 finished at Sat, 07 Feb 2026 15:53:20 +0000. Datasource DataSourceNoCloud [seed=/dev/ss
[  OK  ] Finished cloud-final.service - Cloud-init: Final Stage.
[  OK  ] Reached target cloud-init.target - Cloud-init target.
```

说明cloud init已经启动完成



### 验证

连接qemu

```
ssh -p 2222 ubuntu@localhost
```

密码：mypassword

```
ubuntu@cloudinit-vm:~$ cloud-init status --wait
status: done
ubuntu@cloudinit-vm:~$ systemctl is-active nginx
active
ubuntu@cloudinit-vm:~$ curl http://localhost
Welcome from cloud-init!
```



> 退出qemu的-nographic 模式
>
> Ctrl + A 然后松开，再按 X



## kvm实验

创建ubuntu pvc

```
# ubuntu-nfs-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ubuntu-vm-disk
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: nfs
  
 
 # kubectl apply -f ubuntu-vm-nfs-pvc.yaml -n ai-deliver
```

开启带有cloud-init的vm

```
# test-ubuntu-vm.yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: test-ubuntu-vm
spec:
  running: true
  template:
    spec:
      domain:
        cpu:
          cores: 2
        memory:
          guest: 2Gi
        devices:
          disks:
            - name: rootdisk
              disk:
                bus: virtio
            - name: cloudinitdisk
              disk:
                bus: virtio
          interfaces:
            - name: default
              bridge: {}
      networks:
        - name: default
          pod: {}
      volumes:
        - name: rootdisk
          persistentVolumeClaim:
            claimName: ubuntu-vm-disk
        - name: cloudinitdisk
          cloudInitNoCloud:
            userData: |
              #cloud-config
              hostname: test-ubuntu-vm
              users:
                - name: ubuntu
                  sudo: ALL=(ALL) NOPASSWD:ALL
                  shell: /bin/bash
                  passwd: "$6$rounds=4096$Ccuv.efsv9eRS4lt$hljy/A1jpeKZpi4L1KHY.pYJCO.kn5bWsd.a.wO/rhmGhvv6XyUWMv.rlSVu/DbmiCZyPF3alkIzZVguaVa010"
              ssh_pwauth: true
              resize_rootfs: false
              chpasswd:
                expire: false
                list: |
                  ubuntu:$6$rounds=4096$Ccuv.efsv9eRS4lt$hljy/A1jpeKZpi4L1KHY.pYJCO.kn5bWsd.a.wO/rhmGhvv6XyUWMv.rlSVu/DbmiCZyPF3alkIzZVguaVa010
              packages:
                - curl
                - tree
              runcmd:
                - echo "Cloud-init works!" > /home/ubuntu/cloud-init-test.txt
                - chown ubuntu:ubuntu /home/ubuntu/cloud-init-test.txt

# kubectl apply -f test-ubuntu-vm.yaml -n ai-deliver
# kubectl virt console test-ubuntu-vm -n ai-deliver
```

- password明文会泄露，可生成哈希值openssl passwd -6 -salt salt12345 123456 或 python3 -c "import crypt; print(crypt.crypt('123456', crypt.mksalt(crypt.METHOD_SHA512)))"
- ssh_pwauth: true显式启用，使得可通过ssh ubuntu@ip + 密码登录
- 如果 running: false，apply后vm的状态是stopped，需要kubectl virt start test-ubuntu-vm

> 加了chpasswd才能登录成功
>
> 因为没有chpasswd的情况下，只在users列表里设置了name, sudo, shell, passwd，但仅靠users[].passwd并不能保证密码被正确应用到系统账户上
>
> ```
> chpasswd:
>   expire: false
>   list: |
>     ubuntu:$6$roxxxxxxxxxxxxxxxx
> ```
>
> 这段配置做了两件事情
>
> - 明确将ubuntu用户的密码哈希写入系统
>   - cloud-init 会调用类似 echo "ubuntu:<hash>" | chpasswd -e 的命令（-e 表示输入已是加密哈希）
>   - 这确保 /etc/shadow 中 ubuntu 的密码字段被正确设置为你的 SHA-512 哈希
> - expire: false 防止密码过期
>   - 避免用户首次登录时被强制改密码（这在自动化场景中很关键）
>
> users[].passwd只是声明密码，加了chpasswd才是真正把密码写进了系统

```
jcjy@jcjy-msi:~/xsy-project/cloud-init$ kubectl virt console test-ubuntu-vm -n ai-deliver
Successfully connected to test-ubuntu-vm console. Press Ctrl+] or Ctrl+5 to exit console.
                                                                                         jcjy@jcjy-msi:~/xsy-project/cloud-init$ 
```

没有办法enter登录，因为没有在pvc中导入镜像

需要先关掉vm，因为当 VM 处于 Running 状态时，它的 Pod（virt-launcher-xxx）会独占挂载 PVC，如果importer pod去写同一个pvc，会出现文件系统损坏，写入失败等问题

### 导入镜像

停止vm

```
kubectl virt stop test-ubuntu-vm -n ai-deliver
```

等待状态变为stopped

```
kubectl get vm test-ubuntu-vm -n ai-deliver
# STATUS 应该变成 Stopped
```

创建importer pod，将ubuntu镜像写入pvc

```
# import-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: import-ubuntu-image
  namespace: ai-deliver
spec:
  containers:
    - name: importer
      image: ubuntu:24.04
      command: ["/bin/bash", "-c"]
      args:
        - |
          set -ex
          apt-get update && apt-get install -y wget qemu-utils
          wget -O /tmp/ubuntu.img https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img
          qemu-img convert -f qcow2 -O raw /tmp/ubuntu.img /data/disk.img
          echo "Import completed."
      volumeMounts:
        - name: target
          mountPath: /data
  volumes:
    - name: target
      persistentVolumeClaim:
        claimName: ubuntu-vm-disk
  restartPolicy: OnFailure
  
  
# kubectl apply -f import-ubuntu.yaml -n ai-deliver
```

输出为 disk.img（即使它是 raw 格式），很多kubevirt（尤其是旧版）对disl.raw支持不完善，或不认识

查看日志

```
$ kubectl logs -f import-ubuntu-image -n ai-deliver
...

2026-02-08 13:24:37 (1.67 MB/s) - '/tmp/ubuntu.img' saved [626655744/626655744]

+ qemu-img convert -f qcow2 -O raw /tmp/ubuntu.img /data/disk.raw
+ echo 'Import completed.'
Import completed.
```

等待导入完成

```
$ kubectl get pod import-ubuntu-image -n ai-deliver
NAME                  READY   STATUS      RESTARTS   AGE
import-ubuntu-image   0/1     Completed   0          8m37s
```

### 继续验证kvm是否完成cloud-init

启动vm

```
kubectl virt start test-ubuntu-vm -n ai-deliver
```

连接控制台

```
kubectl virt console test-ubuntu-vm -n ai-deliver
# 按 Enter → 登录 ubuntu / 123456
```

密码123456登录失败，改了很多次后把vm stop, apply再start，还是报错Login incorrect

[Module reference - cloud-init 25.3 documentation](https://cloudinit.readthedocs.io/en/latest/reference/modules.html?spm=5176.28103460.0.0.b2e87551SG7rKh#users-and-groups)

猜测

cloud-init只在首次启动时运行一次，ubuntu会记录一个instance-id（用于磁盘UUID或DMI信息），只要这个ID不变，后续重启VM时cloud-init会跳过所有配置（包括用户密码的设置）

> 之前启动过这个vm，所以instance-id已生成，/var/lib/cloud/instance/ 目录已存在，新 user-data 被完全忽略

所以全部重来一下试试

```
kubectl delete vm test-ubuntu-vm -n ai-deliver

kubectl delete pvc ubuntu-vm-disk -n ai-deliver

kubectl delete pod import-ubuntu-image -n ai-deliver
```



每次import pod的时候都wget好慢，所以做成hostpath的，加了chpasswd后成功了！



### 查看cloud-init创建的内容

```
cd /var/lib/cloud/instance/
```

如果要重新启动cloud-init，需要把这个目录全部删完（最方便的就是把pvc删了）

```
ubuntu@test-ubuntu-vm:/var/lib/cloud/instance$ ls
boot-finished     network-config.json  user-data.txt      vendor-data2.txt
cloud-config.txt  obj.pkl              user-data.txt.i    vendor-data2.txt.i
datasource        scripts              vendor-data.txt
handlers          sem                  vendor-data.txt.i
```



| **文件/目录**          | **作用**                                                     |
| ---------------------- | ------------------------------------------------------------ |
| **`user-data.txt`**    | **最核心文件**。存放你创建虚拟机时填写的自定义脚本或配置。   |
| **`boot-finished`**    | 一个空文件。如果它存在，说明 `cloud-init` 已经跑完了所有流程。 |
| **`datasource`**       | 记录这台机器是从哪获取配置的（比如 AWS、OpenStack 或阿里云）。 |
| **`scripts/`**         | 存放系统启动时需要执行的自定义脚本。                         |
| **`cloud-config.txt`** | 最终生效的云配置汇总。                                       |



还可以看一下初始化日志

```
ubuntu@test-ubuntu-vm:/var/lib/cloud/instance$ sudo cat /var/cat /var/log/cloud-init-output.log
Cloud-init v. 25.2-0ubuntu1~24.04.1 running 'init-local' at Sun, 08 Feb 2026 15:16:15 +0000. Up 3.86 seconds.
Cloud-init v. 25.2-0ubuntu1~24.04.1 running 'init' at Sun, 08 Feb 2026 15:16:18 +0000. Up 6.50 seconds.
ci-info: +++++++++++++++++++++++++++++++++++++++Net device info+++++++++++++++++++++++++++++++++++++++
ci-info: +--------+------+------------------------------+---------------+--------+-------------------+
ci-info: | Device |  Up  |           Address            |      Mask     | Scope  |     Hw-Address    |
ci-info: +--------+------+------------------------------+---------------+--------+-------------------+
ci-info: | enp1s0 | True |         10.244.0.96          | 255.255.255.0 | global | 8a:e1:11:73:70:8e |
ci-info: | enp1s0 | True | fe80::88e1:11ff:fe73:708e/64 |       .       |  link  | 8a:e1:11:73:70:8e |
ci-info: |   lo   | True |          127.0.0.1           |   255.0.0.0   |  host  |         .         |
ci-info: |   lo   | True |           ::1/128            |       .       |  host  |         .         |
ci-info: +--------+------+------------------------------+---------------+--------+-------------------+
ci-info: +++++++++++++++++++++++++++++Route IPv4 info++++++++++++++++++++++++++++++
ci-info: +-------+-------------+------------+-----------------+-----------+-------+
ci-info: | Route | Destination |  Gateway   |     Genmask     | Interface | Flags |
ci-info: +-------+-------------+------------+-----------------+-----------+-------+
ci-info: |   0   |   0.0.0.0   | 10.244.0.1 |     0.0.0.0     |   enp1s0  |   UG  |
ci-info: |   1   |  10.96.0.10 | 10.244.0.1 | 255.255.255.255 |   enp1s0  |  UGH  |
ci-info: |   2   |  10.244.0.0 |  0.0.0.0   |  255.255.255.0  |   enp1s0  |   U   |
ci-info: |   3   |  10.244.0.1 |  0.0.0.0   | 255.255.255.255 |   enp1s0  |   UH  |
ci-info: +-------+-------------+------------+-----------------+-----------+-------+
ci-info: +++++++++++++++++++Route IPv6 info+++++++++++++++++++
ci-info: +-------+-------------+---------+-----------+-------+
ci-info: | Route | Destination | Gateway | Interface | Flags |
ci-info: +-------+-------------+---------+-----------+-------+
ci-info: |   0   |  fe80::/64  |    ::   |   enp1s0  |   U   |
ci-info: |   2   |    local    |    ::   |   enp1s0  |   U   |
ci-info: |   3   |  multicast  |    ::   |   enp1s0  |   U   |
ci-info: +-------+-------------+---------+-----------+-------+
2026-02-08 15:16:18,456 - loggers.py[DEPRECATED]: Deprecated cloud-config provided: chpasswd.list:  Deprecated in version 22.2. Use **users** instead.
2026-02-08 15:16:19,154 - lifecycle.py[DEPRECATED]: Config key 'lists' is deprecated in 22.3 and scheduled to be removed in 27.3. Use 'users' instead.
2026-02-08 15:16:19,154 - lifecycle.py[DEPRECATED]: The chpasswd multiline string is deprecated in 22.2 and scheduled to be removed in 27.2. Use string type instead.
Generating public/private rsa key pair.
Your identification has been saved in /etc/ssh/ssh_host_rsa_key
Your public key has been saved in /etc/ssh/ssh_host_rsa_key.pub
The key fingerprint is:
SHA256:eZqJ737YjmeD7TmeYFvYrlff5o9E3uG8+PPXrx2rTBI root@test-ubuntu-vm
The key's randomart image is:
+---[RSA 3072]----+
|                 |
|                 |
|                 |
|         .       |
|        S .E  .. |
|       . B  ooo..|
|      . B=oo oo=o|
|       oo*Xo+.o+O|
|       oBXBo +=B%|
+----[SHA256]-----+
Generating public/private ecdsa key pair.
Your identification has been saved in /etc/ssh/ssh_host_ecdsa_key
Your public key has been saved in /etc/ssh/ssh_host_ecdsa_key.pub
The key fingerprint is:
SHA256:Et66YuPZl4oX+nwsdLJBhxgeVrr8aEqYMUtwd45le6E root@test-ubuntu-vm
The key's randomart image is:
+---[ECDSA 256]---+
|     ..          |
|    +.           |
|. .oo+=..        |
|.. ooOo=..       |
|o.  +.E.S        |
|.*   o=+.        |
|+ . oooB .       |
| . o==+.=        |
|  .o+=*=         |
+----[SHA256]-----+
Generating public/private ed25519 key pair.
Your identification has been saved in /etc/ssh/ssh_host_ed25519_key
Your public key has been saved in /etc/ssh/ssh_host_ed25519_key.pub
The key fingerprint is:
SHA256:4tp9xOYoe8QnL79Om2hND4EuEfWOwAWwgp87FxvJQpE root@test-ubuntu-vm
The key's randomart image is:
+--[ED25519 256]--+
|  .....oo        |
| .E. o.. .       |
|. o . o. ..      |
| o + ....o.      |
|  + = .+S...     |
|   o =..= B      |
|  o o .o @.o     |
|   o o..=o=o.    |
|    . o=o=*.     |
+----[SHA256]-----+
Cloud-init v. 25.2-0ubuntu1~24.04.1 running 'modules:config' at Sun, 08 Feb 2026 15:16:19 +0000. Up 7.85 seconds.
Cloud-init v. 25.2-0ubuntu1~24.04.1 running 'modules:final' at Sun, 08 Feb 2026 15:16:22 +0000. Up 10.18 seconds.
Get:1 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]
Hit:2 http://archive.ubuntu.com/ubuntu noble InRelease
Get:3 http://archive.ubuntu.com/ubuntu noble-updates InRelease [126 kB]
Get:4 http://archive.ubuntu.com/ubuntu noble-backports InRelease [126 kB]
Get:5 http://security.ubuntu.com/ubuntu noble-security/main amd64 Packages [1431 kB]
Get:6 http://archive.ubuntu.com/ubuntu noble/universe amd64 Packages [15.0 MB]
Get:7 http://security.ubuntu.com/ubuntu noble-security/main Translation-en [232 kB]
Get:8 http://security.ubuntu.com/ubuntu noble-security/main amd64 Components [21.5 kB]
Get:9 http://security.ubuntu.com/ubuntu noble-security/main amd64 c-n-f Metadata [9888 B]
Get:10 http://security.ubuntu.com/ubuntu noble-security/universe amd64 Packages [929 kB]
Get:11 http://security.ubuntu.com/ubuntu noble-security/universe Translation-en [212 kB]
Get:12 http://security.ubuntu.com/ubuntu noble-security/universe amd64 Components [74.2 kB]
Get:13 http://security.ubuntu.com/ubuntu noble-security/universe amd64 c-n-f Metadata [19.9 kB]
Get:14 http://security.ubuntu.com/ubuntu noble-security/restricted amd64 Packages [2411 kB]
Get:15 http://security.ubuntu.com/ubuntu noble-security/restricted Translation-en [553 kB]
Get:16 http://security.ubuntu.com/ubuntu noble-security/restricted amd64 Components [212 B]
Get:17 http://security.ubuntu.com/ubuntu noble-security/restricted amd64 c-n-f Metadata [536 B]
Get:18 http://security.ubuntu.com/ubuntu noble-security/multiverse amd64 Packages [28.8 kB]
Get:19 http://security.ubuntu.com/ubuntu noble-security/multiverse Translation-en [6492 B]
Get:20 http://security.ubuntu.com/ubuntu noble-security/multiverse amd64 Components [212 B]
Get:21 http://security.ubuntu.com/ubuntu noble-security/multiverse amd64 c-n-f Metadata [396 B]
Get:22 http://archive.ubuntu.com/ubuntu noble/universe Translation-en [5982 kB]
Get:23 http://archive.ubuntu.com/ubuntu noble/universe amd64 Components [3871 kB]
Get:24 http://archive.ubuntu.com/ubuntu noble/universe amd64 c-n-f Metadata [301 kB]
Get:25 http://archive.ubuntu.com/ubuntu noble/multiverse amd64 Packages [269 kB]
Get:26 http://archive.ubuntu.com/ubuntu noble/multiverse Translation-en [118 kB]
Get:27 http://archive.ubuntu.com/ubuntu noble/multiverse amd64 Components [35.0 kB]
Get:28 http://archive.ubuntu.com/ubuntu noble/multiverse amd64 c-n-f Metadata [8328 B]
Get:29 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages [1739 kB]
Get:30 http://archive.ubuntu.com/ubuntu noble-updates/main Translation-en [324 kB]
Get:31 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Components [175 kB]
Get:32 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 c-n-f Metadata [16.5 kB]
Get:33 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 Packages [1528 kB]
Get:34 http://archive.ubuntu.com/ubuntu noble-updates/universe Translation-en [313 kB]
Get:35 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 Components [386 kB]
Get:36 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 c-n-f Metadata [31.9 kB]
Get:37 http://archive.ubuntu.com/ubuntu noble-updates/restricted amd64 Packages [2582 kB]
Get:38 http://archive.ubuntu.com/ubuntu noble-updates/restricted Translation-en [591 kB]
Get:39 http://archive.ubuntu.com/ubuntu noble-updates/restricted amd64 Components [212 B]
Get:40 http://archive.ubuntu.com/ubuntu noble-updates/restricted amd64 c-n-f Metadata [556 B]
Get:41 http://archive.ubuntu.com/ubuntu noble-updates/multiverse amd64 Packages [32.1 kB]
Get:42 http://archive.ubuntu.com/ubuntu noble-updates/multiverse Translation-en [6816 B]
Get:43 http://archive.ubuntu.com/ubuntu noble-updates/multiverse amd64 Components [940 B]
Get:44 http://archive.ubuntu.com/ubuntu noble-updates/multiverse amd64 c-n-f Metadata [496 B]
Get:45 http://archive.ubuntu.com/ubuntu noble-backports/main amd64 Packages [40.4 kB]
Get:46 http://archive.ubuntu.com/ubuntu noble-backports/main Translation-en [9208 B]
Get:47 http://archive.ubuntu.com/ubuntu noble-backports/main amd64 Components [7308 B]
Get:48 http://archive.ubuntu.com/ubuntu noble-backports/main amd64 c-n-f Metadata [368 B]
Get:49 http://archive.ubuntu.com/ubuntu noble-backports/universe amd64 Packages [29.5 kB]
Get:50 http://archive.ubuntu.com/ubuntu noble-backports/universe Translation-en [17.9 kB]
Get:51 http://archive.ubuntu.com/ubuntu noble-backports/universe amd64 Components [10.5 kB]
Get:52 http://archive.ubuntu.com/ubuntu noble-backports/universe amd64 c-n-f Metadata [1444 B]
Get:53 http://archive.ubuntu.com/ubuntu noble-backports/restricted amd64 Components [216 B]
Get:54 http://archive.ubuntu.com/ubuntu noble-backports/restricted amd64 c-n-f Metadata [116 B]
Get:55 http://archive.ubuntu.com/ubuntu noble-backports/multiverse amd64 Components [212 B]
Get:56 http://archive.ubuntu.com/ubuntu noble-backports/multiverse amd64 c-n-f Metadata [116 B]
Fetched 39.8 MB in 31s (1286 kB/s)
Reading package lists...
Reading package lists...
Building dependency tree...
Reading state information...
curl is already the newest version (8.5.0-2ubuntu10.6).
curl set to manually installed.
The following NEW packages will be installed:
  tree
0 upgraded, 1 newly installed, 0 to remove and 91 not upgraded.
Need to get 47.4 kB of archives.
After this operation, 111 kB of additional disk space will be used.
Get:1 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 tree amd64 2.1.1-2ubuntu3.24.04.2 [47.4 kB]
Fetched 47.4 kB in 2s (27.7 kB/s)
Selecting previously unselected package tree.
(Reading database ... 74812 files and directories currently installed.)
Preparing to unpack .../tree_2.1.1-2ubuntu3.24.04.2_amd64.deb ...
Unpacking tree (2.1.1-2ubuntu3.24.04.2) ...
Setting up tree (2.1.1-2ubuntu3.24.04.2) ...
Processing triggers for man-db (2.12.0-4build2) ...

Running kernel seems to be up-to-date.

No services need to be restarted.

No containers need to be restarted.

No user sessions are running outdated binaries.

No VM guests are running outdated hypervisor (qemu) binaries on this host.
Cloud-init v. 25.2-0ubuntu1~24.04.1 finished at Sun, 08 Feb 2026 15:17:01 +0000. Datasource DataSourceNoCloud [seed=/dev/vdb].  Up 48.66 seconds
```



