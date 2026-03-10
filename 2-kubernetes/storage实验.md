```
Pod 里的 Volume
│
├── Pod 生命周期级
│   ├── emptyDir
│   └── configMap / secret
│
├── Node 级
│   └── hostPath（⚠️ 强绑定 Node）
│
└── 集群级（真正的持久化）
    ├── PV（管理员资源）
    ├── PVC（用户声明）
    └── StorageClass（动态创建 PV 的模板）
```



## configMap

配置与镜像解耦

验证：改配置 !== 重建镜像

configMap本质是key-->value，使用方式是环境变量、文件volume

---

### 创建configMap，绑到pod上

创建configMap

```
# cm.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: xsy-test-config
data:
  app.conf: |
    APP_NAME=storage-lab
    LOG_LEVEL=debug


# kubectl apply -f cm.yaml -n ai-deliver
# kubectl delete configmap xsy-test-config -n ai-deliver

```

key就是 app.conf

```
kubectl apply -f cm.yaml -n ai-deliver
```

阅读xsy-test-config的信息

```
jcjy@jcjy-msi:~$ kubectl get configMap -n ai-deliver
NAME                                            DATA   AGE
xsy-test-config                                 1      24s
...

jcjy@jcjy-msi:~$ kubectl describe configmap xsy-test-config -n ai-deliver
Name:         xsy-test-config
Namespace:    ai-deliver
Labels:       <none>
Annotations:  <none>

Data
====
app.conf:
----
APP_NAME=storage-lab
LOG_LEVEL=debug



BinaryData
====

Events:  <none>
```

pod中的volume挂载

```
# configMap-pod.yaml

apiVersion: v1
kind: Pod
metadata:
  name: cm-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "cat /config/app.conf && sleep 3600"]
    volumeMounts:
    - name: config
      mountPath: /config
      # subPath: app.conf       # 也可以只挂载 app.conf 这个键
  volumes:
  - name: config
    configMap:
      name: xsy-test-config

# kubectl apply -f configMap-pod.yaml -n ai-deliver

```

创建pod

```
kubectl apply -f configMap-pod.yaml -n ai-deliver
```

可验证configMap已被挂载到pod上

```
jcjy@jcjy-msi:~$ kubectl logs cm-pod -n ai-deliver
APP_NAME=storage-lab
LOG_LEVEL=debug
```



### 修改 configMap 内容（不重建pod）

```
kubectl edit configmap xsy-test-config -n ai-deliver
```

将 LOG_LEVEL=debug 改为 LOG_LEVEL=info

不重启pod，直接查看/config/app.conf

```
jcjy@jcjy-msi:~$ kubectl exec cm-pod -n ai-deliver -- cat /config/app.conf
APP_NAME=storage-lab
LOG_LEVEL=info
```

可以确认config已更新

具体流程

1. pod 被调度到某个node
2. kubelet发现pod引用了 `xsy-test-config` 的configMap
3. kubelet从api server获取 ConfigMap 数据
4. 在节点上创建一个目录（如 `/var/lib/kubelet/pods/<pod-id>/volumes/kubernetes.io～configmap/config/`）
5. 把每个 key 写成一个文件（如 `app.conf`）
6. 通过bind mount把这个目录挂载进容器的 `/config`
7. **后续**：kubelet 每隔一段时间（默认 1 分钟）检查 ConfigMap 是否更新，如果更新，就重写文件



## emptyDir

pod 创建 → 创建

pod 删除 → 数据消失

container崩溃 → 数据保留

### 双容器共享数据

创建pod

```
# emptydir-pod.yaml

apiVersion: v1
kind: Pod
metadata:
  name: emptydir-pod
spec:
  containers:
  - name: writer
    image: busybox
    command: ["sh", "-c", "echo hello k8s > /data/msg && sleep 3600"]
    volumeMounts:
    - name: data
      mountPath: /data

  - name: reader
    image: busybox
    command: ["sh", "-c", "cat /data/msg && sleep 3600"]
    volumeMounts:
    - name: data
      mountPath: /data

  volumes:
  - name: data
    emptyDir: {}

# kubectl apply -f emptydir-pod.yaml -n ai-deliver
# kubectl delete pod emptydir-pod -n ai-deliver

```

两个容器，分别负责读写

验证双容器共享数据

```
jcjy@jcjy-msi:~$ kubectl logs emptydir-pod -c reader -n ai-deliver
hello k8s
```



#### 实际当pod被调度到node上，kubelet负责创建这个空目录，找到目录的具体位置

emptyDir 卷会在每个节点的 `/var/lib/kubelet/pods/<pod-uid>/volumes/kubernetes.io~empty-dir/<volume-name>` 路径下创建

获取pod的UID

```
jcjy@jcjy-msi:~$ kubectl get pod emptydir-pod -n ai-deliver -o jsonpath='{.metadata.uid}'
5c3ea4aa-3e97-4a74-9019-38902a19acbe
```

找到pod运行的节点

```
jcjy@jcjy-msi:~$ kubectl get pod emptydir-pod -n ai-deliver -o wide
NAME           READY   STATUS    RESTARTS   AGE   IP            NODE       NOMINATED NODE   READINESS GATES
emptydir-pod   2/2     Running   0          42m   10.244.0.24   jcjy-msi   <none>           <none>
```

在该节点上查找路径

```
jcjy@jcjy-msi:~$ sudo ls -la /var/lib/kubelet/pods/5c3ea4aa-3e97-4a74-9019-38902a19acbe/volumes/kubernetes.io~empty-dir/
total 12
drwxr-xr-x 3 root root 4096 Feb  3 05:08 .
drwxr-x--- 4 root root 4096 Feb  3 05:08 ..
drwxrwxrwx 2 root root 4096 Feb  3 05:08 data

jcjy@jcjy-msi:~$ sudo ls -la /var/lib/kubelet/pods/5c3ea4aa-3e97-4a74-9019-38902a19acbe/volumes/kubernetes.io~empty-dir/data
total 12
drwxrwxrwx 2 root root 4096 Feb  3 05:08 .
drwxr-xr-x 3 root root 4096 Feb  3 05:08 ..
-rw-r--r-- 1 root root   10 Feb  3 05:08 msg

jcjy@jcjy-msi:~$ sudo cat /var/lib/kubelet/pods/5c3ea4aa-3e97-4a74-9019-38902a19acbe/volumes/kubernetes.io~empty-dir/data/ms
g
hello k8s
```



### 容器崩溃，数据保留

新建pod

```
# crash-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: crash-pod
spec:
  restartPolicy: OnFailure
  containers:
    - name: app
      image: busybox
      command: ['sh', '-c']
      args:
        - |
          echo "$(date): run $(cat /data/count.txt 2>/dev/null || echo 0)" >> /data/log.txt;
          COUNT=$(cat /data/count.txt 2>/dev/null || echo 0);
          echo $((COUNT + 1)) > /data/count.txt;
          cat /data/log.txt;
          exit 1   # 故意崩溃
      volumeMounts:
        - name: temp
          mountPath: /data
  volumes:
    - name: temp
      emptyDir: {}

# kubectl apply -f crash-pod.yaml -n ai-deliver
# kubectl delete pod crash-pod -n ai-deliver

```

验证是否容器不断重启，emptyDir数据依旧保留

```
jcjy@jcjy-msi:~$ kubectl get pod crash-pod -n ai-deliver
NAME        READY   STATUS   RESTARTS      AGE
crash-pod   0/1     Error    3 (28s ago)   44s

jcjy@jcjy-msi:~$ kubectl logs crash-pod -n ai-deliver
Tue Feb  3 05:23:40 UTC 2026: run 0
Tue Feb  3 05:23:41 UTC 2026: run 1
Tue Feb  3 05:23:55 UTC 2026: run 2
Tue Feb  3 05:24:22 UTC 2026: run 3

```

当把pod删除，再重新创建后，可看到emptyDir被清空

可验证emptyDir与pod同生命周期

```
jcjy@jcjy-msi:~$ kubectl delete pod crash-pod -n ai-deliver
pod "crash-pod" deleted

jcjy@jcjy-msi:~/xsy-project/k8s/storage/script/emptyDir$ kubectl apply -f crash-pod.yaml -n ai-deliver
pod/crash-pod created

jcjy@jcjy-msi:~$ kubectl logs crash-pod -n ai-deliver
Tue Feb  3 05:27:40 UTC 2026: run 0
```



## hostPath

pod **必须调度到同一个node**，不可迁移

新增 pod

```
apiVersion: v1
kind: Pod
metadata:
  name: hostpath-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo hostpath-test > /data/msg && sleep 3600"]
    volumeMounts:
    - name: host
      mountPath: /data
  volumes:
  - name: host
    hostPath:
      path: /tmp/k8s-hostpath
      type: DirectoryOrCreate

# kubectl apply -f hostPath-pod.yaml -n ai-deliver
# kubectl delete pod hostpath-pod -n ai-deliver

```

验证hostPath是否绕过k8s存储，由kubelet直接mount node目录

```
jcjy@jcjy-msi:~$ cat /tmp/k8s-hostpath/msg
hostpath-test
```



## storageClass

使用已有storageClass，查看pv是否创建，及不同volumeBindingMode下的pv创建时机

> 先不创建storageClass，因为搞不懂provisioner

查看现有storageClass

```
jcjy@jcjy-msi:~$ kubectl get storageclass -n ai-deliver
NAME               PROVISIONER                  RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
local-path         rancher.io/local-path        Delete          WaitForFirstConsumer   false                  75d
nfs (default)      nfs.csi.k8s.io               Retain          Immediate              false                  157d
openebs-hostpath   openebs.io/local             Delete          WaitForFirstConsumer   false                  157d
rook-ceph-block    rook-ceph.rbd.csi.ceph.com   Delete          Immediate              true                   75d
```



### 使用local-path(WaitForFirstConsumer)

创建pvc

```
# sc-pvc-local.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-local-test
spec:
  storageClassName: local-path
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi

# kubectl apply -f sc-pvc-local.yaml -n ai-deliver
# kubectl delete pvc pvc-local-test -n ai-deliver

```

查看pvc状态

```
jcjy@jcjy-msi:~$ kubectl get pvc pvc-local-test -n ai-deliver
NAME             STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
pvc-local-test   Pending                                      local-path     <unset>                 46s
jcjy@jcjy-msi:~$
```

符合预期，因为volumeBindingMode: WaitForFirstConsumer，还没pod，所以还没pv

确认pv是否也没有创建

```
kubectl get pv -n ai-deliver
```

创建pod绑定该pvc

```
# pod-with-pvc-local.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-pvc-local
spec:
  containers:
    - name: writer
      image: busybox
      command: ["/bin/sh", "-c"]
      args:
        - |
          echo "$(date): Hello from $(hostname)" >> /data/message.txt;
          cat /data/message.txt;
          sleep 3600
      volumeMounts:
        - name: vol
          mountPath: /data
  volumes:
    - name: vol
      persistentVolumeClaim:
        claimName: pvc-local-test

# kubectl apply -f pod-with-pvc-local.yaml -n ai-deliver


```

但pod状态与预期不符

```
jcjy@jcjy-msi:~$ kubectl describe pod pod-with-pvc-local -n ai-deliver
Name:             pod-with-pvc-local
Namespace:        ai-deliver
Priority:         0
Service Account:  default
Node:             <none>
Labels:           <none>
Annotations:      <none>
Status:           Pending
IP:
IPs:              <none>
Containers:
  writer:
    Image:      busybox
    Port:       <none>
    Host Port:  <none>
    Command:
      /bin/sh
      -c
    Args:
      echo "$(date): Hello from $(hostname)" >> /data/message.txt;
      cat /data/message.txt;
      sleep 3600

    Environment:  <none>
    Mounts:
      /data from vol (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-nx2tg (ro)
Volumes:
  vol:
    Type:       PersistentVolumeClaim (a reference to a PersistentVolumeClaim in the same namespace)
    ClaimName:  pvc-local-test
    ReadOnly:   false
  kube-api-access-nx2tg:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    Optional:                false
    DownwardAPI:             true
QoS Class:                   BestEffort
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:                      <none>
```

pod 状态为 `Pending` 且没有分配到节点，原因是 pvc `pvc-local-test` 状态也是 `Pending`，无法绑定

pvc 要等到有 pod 使用它时才会绑定和创建pv，但是pod却因为pvc未绑定而无法调度，形成死锁

```
jcjy@jcjy-msi:~$ kubectl get storageclass local-path -o yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: |
      {"apiVersion":"storage.k8s.io/v1","kind":"StorageClass","metadata":{"annotations":{},"name":"local-path"},"provisioner":"rancher.io/local-path","reclaimPolicy":"Delete","volumeBindingMode":"WaitForFirstConsumer"}
  creationTimestamp: "2025-11-20T01:50:17Z"
  name: local-path
  resourceVersion: "29279910"
  uid: 6760fc0e-d1c0-4ac5-84be-3c155a7ba16e
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
jcjy@jcjy-msi:~$ kubectl get pods -A -l app.kubernetes.io/name=local-path-provisioner
No resources found
jcjy@jcjy-msi:~$
```

原因是storageClass local-path配置了 provisioner: rancher.io/local-path，但集群中没有对应的provisioner pod

#### 安装local-path provisioner

```
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
```

等待provisoner启动

```
jcjy@jcjy-msi:~$ kubectl get pods -n local-path-storage -w
NAME                                     READY   STATUS    RESTARTS   AGE
local-path-provisioner-8ffbb88cb-tvkhl   1/1     Running   0          83s
```

---

安装时自动处理了积压的pvc，不用重建，实验继续

```
jcjy@jcjy-msi:~$ kubectl get pvc pvc-local-test -n ai-deliver
NAME             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
pvc-local-test   Bound    pvc-90ce2968-88ad-4d2b-9fc9-586610c80eef   500Mi      RWO            local-path     <unset>   
```

pvc状态为Bound，说明已和pv绑定

```
jcjy@jcjy-msi:~$ kubectl get pv
pvc-90ce2968-88ad-4d2b-9fc9-586610c80eef   500Mi      RWO            Delete           Bound       ai-deliver/pvc-local-test                                local-path         <unset>                          2m52s
...
```

pv已创建，并与pvc绑定

```
jcjy@jcjy-msi:~$ kubectl get pod pod-with-pvc-local -n ai-deliver
NAME                 READY   STATUS    RESTARTS   AGE
pod-with-pvc-local   1/1     Running   0          22m
```

pod可正常运行



### 使用nfs(Immediate)

检查有没有对应的provisioner pod

查看storageClass配置

```
jcjy@jcjy-msi:~$ kubectl describe storageclass nfs
Name:                  nfs
IsDefaultClass:        Yes
Annotations:           meta.helm.sh/release-name=middleware,meta.helm.sh/release-namespace=ai-deliver,storageclass.kubernetes.io/is-default-class=true
Provisioner:           nfs.csi.k8s.io          # 这是 provisioner 名称
Parameters:            mountPermissions=0777,server=192.168.1.150,share=/data/nfs
AllowVolumeExpansion:  <unset>
MountOptions:
  nfsvers=4.0
ReclaimPolicy:      Retain
VolumeBindingMode:  Immediate
Events:             <none>
```

查看正在运行的provisioner pods

```
jcjy@jcjy-msi:~$ kubectl get pods -A | grep -i nfs
ai-deliver           csi-nfs-controller-6fd7c56987-62m2q                         4/4     Running     15 (17d ago)   157d
ai-deliver           csi-nfs-node-lwzcs                                          3/3     Running     11 (67d ago)   157d
```

查看csi driver注册

```
jcjy@jcjy-msi:~$ kubectl get csidriver nfs.csi.k8s.io -o yaml 2>/dev/null
apiVersion: storage.k8s.io/v1
kind: CSIDriver
metadata:
  annotations:
    meta.helm.sh/release-name: middleware
    meta.helm.sh/release-namespace: ai-deliver
  creationTimestamp: "2025-08-29T09:40:25Z"
  labels:
    app.kubernetes.io/managed-by: Helm
  name: nfs.csi.k8s.io           # 已正确注册到 Kubernetes
  resourceVersion: "1035"
  uid: 540b49c3-2324-4063-948e-ea1b72f73e03
spec:
  attachRequired: false
  fsGroupPolicy: File
  podInfoOnMount: false
  requiresRepublish: false
  seLinuxMount: false
  storageCapacity: false
  volumeLifecycleModes:
  - Persistent
```

#### 验证Immediate模式是创建pvc后立刻创建pv绑定

创建pvc

```
# sc-pvc-nfs.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-nfs-test
spec:
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 500Mi

# kubectl apply -f sc-pvc-nfs.yaml -n ai-deliver
# kubectl delete pvc pvc-nfs-test -n ai-deliver

```

观察pvc和pv的状态

```
jcjy@jcjy-msi:~$ kubectl get pvc pvc-nfs-test -n ai-deliver
NAME           STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
pvc-nfs-test   Bound    pvc-1aab48a5-2873-4e2b-b935-3aafd1751679   500Mi      RWX            nfs            <unset>                 13s
```

pvc STATUS=Bound 立刻绑定

```
jcjy@jcjy-msi:~$ kubectl get pv
NAME                                       CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM     pvc-1aab48a5-2873-4e2b-b935-3aafd1751679   500Mi      RWX            Retain           Bound       ai-deliver/pvc-nfs-test                                  nfs                <unset>                          87s
...
```

立刻出现新的pv

### 顺便测试一下pvc的持久化能力

```
jcjy@jcjy-msi:~$ kubectl logs pod-with-pvc-nfs -n ai-deliver
Tue Feb  3 08:09:57 UTC 2026: Hello from pod-with-pvc-nfs
```

重建一个不同名，同pvc name的pod

```
jcjy@jcjy-msi:~$ kubectl logs pod-with-pvc-nfs-2 -n ai-deliver
Tue Feb  3 08:09:57 UTC 2026: Hello from pod-with-pvc-nfs
Tue Feb  3 08:14:19 UTC 2026: Hello from pod-with-pvc-nfs-2
```

额外验证

```
# 查看pvc绑定的pv
jcjy@jcjy-msi:~$ kubectl get pvc pvc-nfs-test -n ai-deliver -o jsonpath='{.spec.volumeName}'
pvc-1aab48a5-2873-4e2b-b935-3aafd1751679

# 查看pv内容
jcjy@jcjy-msi:~$ kubectl get pv pvc-1aab48a5-2873-4e2b-b935-3aafd1751679 -o yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  annotations:
    pv.kubernetes.io/provisioned-by: nfs.csi.k8s.io
    volume.kubernetes.io/provisioner-deletion-secret-name: ""
    volume.kubernetes.io/provisioner-deletion-secret-namespace: ""
  creationTimestamp: "2026-02-03T08:02:58Z"
  finalizers:
  - kubernetes.io/pv-protection
  name: pvc-1aab48a5-2873-4e2b-b935-3aafd1751679
  resourceVersion: "61185878"
  uid: 0d769a66-42d3-44b2-a4f4-45d7ce7e6503
spec:
  accessModes:
  - ReadWriteMany           # 多节点读写，nfs支持，local-path就只能ReadWriteOnce（能否被不同node的pod挂载）
  capacity:
    storage: 500Mi
  claimRef:
    apiVersion: v1
    kind: PersistentVolumeClaim
    name: pvc-nfs-test
    namespace: ai-deliver
    resourceVersion: "61185869"
    uid: 1aab48a5-2873-4e2b-b935-3aafd1751679
  csi:
    driver: nfs.csi.k8s.io
    volumeAttributes:
      csi.storage.k8s.io/pv/name: pvc-1aab48a5-2873-4e2b-b935-3aafd1751679
      csi.storage.k8s.io/pvc/name: pvc-nfs-test
      csi.storage.k8s.io/pvc/namespace: ai-deliver
      mountPermissions: "0777"
      server: 192.168.1.150                 # nfs服务器
      share: /data/nfs                      # 共享路径
      storage.kubernetes.io/csiProvisionerIdentity: 1768556904028-4418-nfs.csi.k8s.io
      subdir: pvc-1aab48a5-2873-4e2b-b935-3aafd1751679   # 实际子目录 /data/nfs/pvc-1aab48a5-2873-4e2b-b935-3aafd1751679
    volumeHandle: 192.168.1.150#data/nfs#pvc-1aab48a5-2873-4e2b-b935-3aafd1751679##
  mountOptions:
  - nfsvers=4.0
  persistentVolumeReclaimPolicy: Retain      # 回收策略：删除pvc后数据保留
  storageClassName: nfs
  volumeMode: Filesystem
status:
  lastPhaseTransitionTime: "2026-02-03T08:02:58Z"
  phase: Bound
```

可以在宿主机本地找到实际pv中存储的内容

```
jcjy@jcjy-msi:~$ cd /data/nfs/pvc-1aab48a5-2873-4e2b-b935-3aafd1751679
jcjy@jcjy-msi:/data/nfs/pvc-1aab48a5-2873-4e2b-b935-3aafd1751679$ ls
message.txt
jcjy@jcjy-msi:/data/nfs/pvc-1aab48a5-2873-4e2b-b935-3aafd1751679$ cat message.txt
Tue Feb  3 08:09:57 UTC 2026: Hello from pod-with-pvc-nfs
Tue Feb  3 08:14:19 UTC 2026: Hello from pod-with-pvc-nfs-2
```













