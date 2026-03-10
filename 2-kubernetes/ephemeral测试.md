场景

pod里挂的storage可以 ephemeral 吗，想装一些东西进去，就是要从外面挂东西进去，学生可以改，但是不会影响原来storage的东西，下次挂进来又恢复了，kvm肯定是可以的   但是pod不知道行不行



### 方案一：ephemeral pvc + initContainer

创建pod

```
apiVersion: v1
kind: Pod
metadata:
  name: student-lab-init
spec:
  restartPolicy: Never

  volumes:
  - name: workdir
    ephemeral:
      volumeClaimTemplate:
        metadata:
          labels:
            purpose: student-workspace
        spec:
          accessModes:
          - ReadWriteOnce
          storageClassName: nfs
          resources:
            requests:
              storage: 5Gi

  initContainers:
  - name: init-workspace
    image: busybox
    command:
    - sh
    - -c
    - |
      echo "Initializing workspace..."
      mkdir -p /work
      echo "Welcome to the lab!" > /work/README.txt
      echo "You can modify anything here." >> /work/README.txt
      mkdir /work/src
      echo 'print("hello student")' > /work/src/main.py
    volumeMounts:
    - name: workdir
      mountPath: /work

  containers:
  - name: lab
    image: python:3.11-slim
    command: ["sleep", "3600"]
    volumeMounts:
    - name: workdir
      mountPath: /workspace

# kubectl apply -f student-lab-initContainer.yaml

# kubectl get pvc
# kubectl exec -it student-lab-init -- bash

# kubectl delete pod student-lab-init

```

可以看到pvc和pod同步生成，同步删除







### 方案二：ephemeral pvc + snapshoot

安装snapshot controller（否则snapshot起不来）

```
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml
```

安装成功

```
jcjy@jcjy-msi:~$ kubectl get pods -n kube-system | grep snapshot-controller
snapshot-controller-fcb6b9c8d-fwc98   1/1     Running     0             19m
snapshot-controller-fcb6b9c8d-gdkjt   1/1     Running     0             20m
```

用 rook-ceph-block 这个 storageClass，原生支持快照

确认CSI Sidecar存在，rook 默认会安装 csi-snapshotter 边车

```
jcjy@jcjy-msi:~/xsy-project/init-ephemeral-pvc$ kubectl get pods -n rook-ceph | grep rbd
rook-ceph.rbd.csi.ceph.com-ctrlplugin-647f9c858b-d2h89      5/5     Running    9 (24d ago)   82d
rook-ceph.rbd.csi.ceph.com-nodeplugin-g8hr4                 2/2     Running    2 (73d ago)   82d
```



发现 replicapool报错

```
jcjy@jcjy-msi:~/xsy-project/init-ephemeral-pvc$ kubectl get cephblockpools replicapool -n rook-ceph
NAME          PHASE     TYPE         FAILUREDOMAIN   AGE
replicapool   Failure   Replicated   host            82d
```



```
jcjy@jcjy-msi:~/xsy-project/init-ephemeral-pvc$ kubectl describe cephblockpools replicapool -n rook-ceph
Name:         replicapool
Namespace:    rook-ceph
Labels:       <none>
Annotations:  <none>
API Version:  ceph.rook.io/v1
Kind:         CephBlockPool
Metadata:
  Creation Timestamp:  2025-11-20T01:33:56Z
  Finalizers:
    cephblockpool.ceph.rook.io
  Generation:        2
  Resource Version:  29275611
  UID:               36fd418f-3ed8-404c-b652-5ded26729db2
Spec:
  Application:  
  Erasure Coded:
    Coding Chunks:  0
    Data Chunks:    0
  Failure Domain:   host
  Mirroring:
  Quotas:
  Replicated:
    Require Safe Replica Size:  true
    Size:                       1
  Status Check:
    Mirror:
Status:
  Cephx:
    Peer Token:
  Info:
    Failure Domain:  host
    Type:            Replicated
  Phase:             Progressing
Events:
  Type     Reason           Age                    From                             Message
  ----     ------           ----                   ----                             -------
  Warning  ReconcileFailed  4m8s (x6059 over 69d)  rook-ceph-block-pool-controller  failed to reconcile CephBlockPool "rook-ceph/replicapool". invalid pool CR "replicapool" spec: error pool size is 1 and requireSafeReplicaSize is true, must be false
```

在线修正

```
kubectl edit cephblockpool replicapool -n rook-ceph
```

把requireSafeReplicaSize: true改为false

继续报错

```
Events:
  Type     Reason           Age                  From                             Message
  ----     ------           ----                 ----                             -------
  Warning  ReconcileFailed  2m29s                rook-ceph-block-pool-controller  failed to reconcile CephBlockPool "rook-ceph/replicapool". failed to create pool "replicapool".: failed to configure pool "replicapool".: failed to initialize pool "replicapool" for RBD use. : signal: interrupt
  Warning  ReconcileFailed  2s (x6060 over 69d)  rook-ceph-block-pool-controller  failed to reconcile CephBlockPool "rook-ceph/replicapool". invalid pool CR "replicapool" spec: error pool size is 1 and requireSafeReplicaSize is true, must be false
```



pvc创建失败

```
Events:
  Type    Reason                Age                From                                                                                                                    Message
  ----    ------                ----               ----                                                                                                                    -------
  Normal  Provisioning          34s                rook-ceph.rbd.csi.ceph.com_rook-ceph.rbd.csi.ceph.com-ctrlplugin-647f9c858b-d2h89_0a573a67-4880-4cfd-b34b-6ec4731a4ca1  External provisioner is provisioning volume for claim "rook-ceph/base-pvc"
  Normal  ExternalProvisioning  14s (x3 over 34s)  persistentvolume-controller                                                                                             Waiting for a volume to be created either by the external provisioner 'rook-ceph.rbd.csi.ceph.com' or manually by the system administrator. If volume creation is delayed, please verify that the provisioner is running and correctly registered.

```



没有OSD

```
jcjy@jcjy-msi:~/xsy-project/init-ephemeral-pvc$ kubectl logs replicapool -n rook-ceph
error: error from server (NotFound): pods "replicapool" not found in namespace "rook-ceph"
```

确认ceph集群没有OSD（存储节点）

```
jcjy@jcjy-msi:~/xsy-project/init-ephemeral-pvc$ kubectl apply -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/toolbox.yaml -n rook-ceph
deployment.apps/rook-ceph-tools created
jcjy@jcjy-msi:~/xsy-project/init-ephemeral-pvc$ kubectl -n rook-ceph exec -it deploy/rook-ceph-tools -- ceph -s
  cluster:
    id:     de5fe941-e56e-4f8c-9a26-a98a3f150f3d
    health: HEALTH_WARN
            Reduced data availability: 1 pg inactive
            1 pool(s) have no replicas configured
            OSD count 0 < osd_pool_default_size 3
 
  services:
    mon: 1 daemons, quorum a (age 9w)
    mgr: a(active, since 9w)
    osd: 0 osds: 0 up, 0 in
 
  data:
    pools:   1 pools, 1 pgs
    objects: 0 objects, 0 B
    usage:   0 B used, 0 B / 0 B avail
    pgs:     100.000% pgs unknown
             1 unknown
 
```

因为ceph-block是块存储，所以需要独占一块硬盘；发送的都是硬盘指令，不是文件指令



换一台机器

创建snapshot时报错

```
status:
  error:
    message: 'Failed to check and update snapshot content: failed to take snapshot
      of the volume 0001-0009-rook-ceph-0000000000000002-7b1df741-27fd-4fd7-87b6-2afd4e76b7cf:
      "rpc error: code = Internal desc = provided secret is empty"'
    time: "2026-02-10T08:10:16Z"
  readyToUse: false
```

调查

```
kubectl get secret rook-csi-rbd-provisioner -n rook-ceph -o yaml
```

发现secret存在且内容非空

```
data:
  userID: Y3NpLXJiZC1wcm92aXNpb25lcg==
  userKey: QVFBajBiVm5EdmZoRmhBQWhGMVJxMHRwc3UzWHVIcXVsOXlKVnc9PQ==
```



```
PS C:\code\xsy\k8s_notes\2-kubernetes\snapshot-pvc> kubectl describe secret rook-csi-rbd-provisioner -n rook-ceph
Name:         rook-csi-rbd-provisioner
Namespace:    rook-ceph
Labels:       <none>
Annotations:  <none>

Type:  kubernetes.io/rook

Data
====
userID:   19 bytes
userKey:  40 bytes
```



snapshot的报错为

```
PS C:\code\xsy\k8s_notes\2-kubernetes\snapshot-pvc> kubectl describe volumesnapshot base-snapshot -n rens-test
Name:         base-snapshot
Namespace:    rens-test
Labels:       <none>
Annotations:  <none>
API Version:  snapshot.storage.k8s.io/v1
Kind:         VolumeSnapshot
Metadata:
  Creation Timestamp:  2026-02-10T10:10:29Z
  Finalizers:
    snapshot.storage.kubernetes.io/volumesnapshot-as-source-protection
    snapshot.storage.kubernetes.io/volumesnapshot-bound-protection
  Generation:  1
  Managed Fields:
    API Version:  snapshot.storage.k8s.io/v1
    Fields Type:  FieldsV1
    fieldsV1:
      f:metadata:
        f:annotations:
          .:
          f:kubectl.kubernetes.io/last-applied-configuration:
      f:spec:
        .:
        f:source:
          .:
          f:persistentVolumeClaimName:
        f:volumeSnapshotClassName:
    Manager:      kubectl-client-side-apply
    Operation:    Update
    Time:         2026-02-10T10:10:29Z
    API Version:  snapshot.storage.k8s.io/v1
    Fields Type:  FieldsV1
    fieldsV1:
      f:metadata:
        f:finalizers:
          .:
          v:"snapshot.storage.kubernetes.io/volumesnapshot-as-source-protection":
          v:"snapshot.storage.kubernetes.io/volumesnapshot-bound-protection":
    Manager:      snapshot-controller
    Operation:    Update
    Time:         2026-02-10T10:10:29Z
    API Version:  snapshot.storage.k8s.io/v1
    Fields Type:  FieldsV1
    fieldsV1:
      f:status:
        .:
        f:boundVolumeSnapshotContentName:
        f:error:
          .:
          f:message:
          f:time:
        f:readyToUse:
    Manager:         snapshot-controller
    Operation:       Update
    Subresource:     status
    Time:            2026-02-10T10:10:31Z
  Resource Version:  291779777
  UID:               237a4cf7-2e5d-4efd-8b72-218c3d8a0028
Spec:
  Source:
    Persistent Volume Claim Name:  base-pvc
  Volume Snapshot Class Name:      lab-snapshot-class
Status:
  Bound Volume Snapshot Content Name:  snapcontent-237a4cf7-2e5d-4efd-8b72-218c3d8a0028
  Error:
    Message:     Failed to check and update snapshot content: failed to take snapshot of the volume 
0001-0009-rook-ceph-0000000000000002-7b1df741-27fd-4fd7-87b6-2afd4e76b7cf: "rpc error: code = Internal desc = provided secret is empty"
    Time:        2026-02-10T10:10:30Z
  Ready To Use:  false
Events:
  Type     Reason                         Age   From                 Message
  ----     ------                         ----  ----                 -------
  Warning  SnapshotFinalizerError         10m   snapshot-controller  Failed to check and update snapshot: snapshot controller failed to update rens-test/base-snapshot on API server: Operation cannot be fulfilled on volumesnapshots.snapshot.storage.k8s.io "base-snapshot": the object has been modified; please apply your changes to the latest version and try again
  Warning  SnapshotFinalizerError         10m   snapshot-controller  Failed to check and update snapshot: snapshot controller failed to update rens-test/base-snapshot on API server: Operation cannot be fulfilled on volumesnapshots.snapshot.storage.k8s.io "base-snapshot": the object has been modified; please apply your changes to the latest version and try again
  Normal   CreatingSnapshot               10m   snapshot-controller  Waiting for a snapshot rens-test/base-snapshot to be created by the CSI driver.
  Warning  SnapshotContentCreationFailed  10m   snapshot-controller  Failed to create snapshot content with error snapshot controller failed to update base-pvc on API server: Operation cannot be fulfilled on persistentvolumeclaims "base-pvc": the object has been modified; please apply your changes to the latest version and try again
```

抄另一个sc的配置

```
kubectl get sc -o yaml
```

```
 parameters:
    clusterID: rook-ceph
    csi.storage.k8s.io/controller-expand-secret-name: rook-csi-rbd-provisioner
    csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
    csi.storage.k8s.io/fstype: ext4
    csi.storage.k8s.io/node-stage-secret-name: rook-csi-rbd-node
    csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
    csi.storage.k8s.io/provisioner-secret-name: rook-csi-rbd-provisioner
    csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
    imageFeatures: layering
    imageFormat: "2"
    pool: replicapool
```

需要新增

```
parameters:
  clusterID: rook-ceph
  csi.storage.k8s.io/snapshotter-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/snapshotter-secret-namespace: rook-ceph
```

创建成功

````
PS C:\code\xsy\k8s_notes\2-kubernetes\snapshot-pvc> kubectl get volumesnapshot -n rens-test
NAME            READYTOUSE   SOURCEPVC   SOURCESNAPSHOTCONTENT   RESTORESIZE   SNAPSHOTCLASS        
SNAPSHOTCONTENT                                    CREATIONTIME   AGE
base-snapshot   true         base-pvc                            10Gi          lab-snapshot-class   
snapcontent-52dde560-bd57-4828-9a62-af7f19339ca2   10s            10s
````









