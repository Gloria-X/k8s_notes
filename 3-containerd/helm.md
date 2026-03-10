# Helm

k8s的包管理器，就像apt之于ubuntu；brew之于macOS

- 定义、安装、升级复杂的k8s应用
- 管理应用的版本（通过 Chart 版本和 Release 历史）
- 共享可复用的应用模板



## concepts

#### Chart

helm的打包格式，包含在k8s中部署应用所需的所有yaml资源文件

#### Repository

存放和发放Chart的地方，类似于软件包仓库

#### Release

Chart在集群中的一次具体安装实例，每次安装都会生成一个唯一的Release

---

helm cli：本地运行的命令工具

直接与api server通信（通过kubeconfig）

所有Release信息以Secret形式存储在目标命令空间中（默认）



### 常用cli

```
# 搜索 Chart
helm search hub <keyword>           # 在 Artifact Hub 搜索
helm search repo <keyword>          # 在本地仓库搜索

# 添加/移除仓库
helm repo add <仓库名> <URL>        # 添加仓库
helm repo list                     # 列出仓库
helm repo update                   # 更新仓库索引
helm repo remove <仓库名>          # 移除仓库

# Chart 操作
helm pull <chart> --untar          # 下载并解压 Chart
helm show values <chart>           # 显示 Chart 的 values
helm show chart <chart>            # 显示 Chart 信息
helm show all <chart>              # 显示所有信息
```

```
# 1. 安装并等待
helm install myapp . --namespace dev --wait --timeout 5m

# 2. 升级并自动回滚
helm upgrade myapp . --atomic --wait

# 3. 查看所有相关信息
helm status myapp && helm get values myapp && helm get manifest myapp | head -50

# 4. 测试模板渲染
helm template myapp . --values values.yaml --debug

# 5. 清理旧版本
helm uninstall myapp && helm install myapp .
```



## chart结构

创建一个测试的chart

```
helm create xsy-chart
```

结构如下

```
jcjy@jcjy-msi:~/xsy-project/helm/xsy-chart$ tree
.
├── charts
├── Chart.yaml
├── templates   # 以下都是资源编排
│   ├── deployment.yaml
│   ├── _helpers.tpl
│   ├── hpa.yaml
│   ├── ingress.yaml
│   ├── NOTES.txt
│   ├── serviceaccount.yaml
│   ├── service.yaml
│   └── tests
│       └── test-connection.yaml
└── values.yaml

3 directories, 10 files
```

查看 Chart.yaml

```
apiVersion: v2
name: xsy-chart
description: A Helm chart for Kubernetes
type: application

# chart打包后的版本，类比docker推到hub上时候的tag
version: 0.1.0

# 表示自己服务的版本，如服务是mysql8.0，这边就能写8.0
appVersion: "1.16.0"
```

charts装该Chart需要的依赖包和服务，很像node_modules

#### 渲染语法

{{ include "web.fullname" . }} 根据include取模板（_helpers.tpl）

{{ xxxx .Values.autoscaling.enabled }} 根据values取值，根据值的是非来判断

{{ xxx with .Values.podAnnotations }} 根据with看有没有在value.yaml里写着属性来判断要不要渲染









## 实验：nginx

### 本地起Chart

#### 安装

安装本地chart

```
helm install xsy-chart . -n ai-deliver
```



```
jcjy@jcjy-msi:~/xsy-project/helm/xsy-chart$ helm install xsy-chart . -n ai-deliver
NAME: xsy-chart
LAST DEPLOYED: Fri Feb  6 12:20:21 2026
NAMESPACE: ai-deliver
STATUS: deployed
REVISION: 1
NOTES:
1. Get the application URL by running these commands:
  export POD_NAME=$(kubectl get pods --namespace ai-deliver -l "app.kubernetes.io/name=xsy-chart,app.kubernetes.io/instance=xsy-chart" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace ai-deliver $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl --namespace ai-deliver port-forward $POD_NAME 8080:$CONTAINER_PORT
```

> 输出可以在NOTES.txt里自定义

查看服务启动

```
jcjy@jcjy-msi:~$ kubectl get pod -n ai-deliver
NAME                                                        READY   STATUS      RESTARTS         AGE
...
xsy-chart-74f7f7f4bf-6n2hd                                  1/1     Running     0                54s


jcjy@jcjy-msi:~$ kubectl get service -n ai-deliver
NAME                                            TYPE           CLUSTER-IP       EXTERNAL-IP                                   PORT(S)                                 AGE
...
xsy-chart                                       ClusterIP      10.111.22.253    <none>                                        80/TCP                                  103s
```

查看helm的版本

```
jcjy@jcjy-msi:~$ helm history xsy-chart -n ai-deliver
REVISION        UPDATED                         STATUS          CHART           APP VERSION     DESCRIPTION
1               Fri Feb  6 12:20:21 2026        deployed        xsy-chart-0.1.0 1.16.0          Install complete
```



#### 升级

升级helm（改个镜像版本）

```
helm upgrade xsy-chart . -n ai-deliver --atomic
```

> --atomic 原子操作，确保升级失败不会导致服务瘫痪

deployment的更新策略，平滑升级

```
jcjy@jcjy-msi:~$ kubectl get pod -n ai-deliver
NAME                                                        READY   STATUS      RESTARTS       AGE
xsy-chart-74f7f7f4bf-6n2hd                                  1/1     Running     0              15m
xsy-chart-7bb946df8b-rltx7                                  0/1     Running     0              5s
```

如果失败了会把创建中的kind（可能好了，可能失败）都删除干净

```
jcjy@jcjy-msi:~/xsy-project/helm/xsy-chart$ helm upgrade xsy-chart . -n ai-deliver --atomic
^CRelease xsy-chart has been cancelled.
Error: UPGRADE FAILED: release xsy-chart failed, and has been rolled back due to atomic being set: context canceled
```

成功了

```
jcjy@jcjy-msi:~/xsy-project/helm/xsy-chart$ helm upgrade xsy-chart . -n ai-deliver --atomic
Release "xsy-chart" has been upgraded. Happy Helming!
NAME: xsy-chart
LAST DEPLOYED: Fri Feb  6 12:35:58 2026
NAMESPACE: ai-deliver
STATUS: deployed
REVISION: 4
NOTES:
1. Get the application URL by running these commands:
  export POD_NAME=$(kubectl get pods --namespace ai-deliver -l "app.kubernetes.io/name=xsy-chart,app.kubernetes.io/instance=xsy-chart" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace ai-deliver $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl --namespace ai-deliver port-forward $POD_NAME 8080:$CONTAINER_PORT
```

确认镜像是改动后的镜像

```
jcjy@jcjy-msi:~$ kubectl get pod  xsy-chart-7bb946df8b-rltx7 -n ai-deliver -o yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    k8s.v1.cni.cncf.io/network-status: |-
      [{
          "name": "cbr0",
          "interface": "eth0",
          "ips": [
              "10.244.0.243"
          ],
          "mac": "12:36:cf:b5:d3:83",
          "default": true,
          "dns": {},
          "gateway": [
              "10.244.0.1"
          ]
      }]
  creationTimestamp: "2026-02-06T12:35:58Z"
  generateName: xsy-chart-7bb946df8b-
  labels:
    app.kubernetes.io/instance: xsy-chart
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/name: xsy-chart
    app.kubernetes.io/version: 1.16.0
    helm.sh/chart: xsy-chart-0.1.0
    pod-template-hash: 7bb946df8b
  name: xsy-chart-7bb946df8b-rltx7
  namespace: ai-deliver
  ownerReferences:
  - apiVersion: apps/v1
    blockOwnerDeletion: true
    controller: true
    kind: ReplicaSet
    name: xsy-chart-7bb946df8b
    uid: b5ca750d-b597-43dd-b355-cac778eda8d0
  resourceVersion: "62615430"
  uid: f3deb684-798a-48a7-ac2c-8e3179f8cf83
spec:
  containers:
  - image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/registry.k8s.io/nginx-slim:0.21
    imagePullPolicy: IfNotPresent

...
```

现在的history

```
jcjy@jcjy-msi:~$ helm history xsy-chart -n ai-deliver
REVISION        UPDATED                         STATUS          CHART           APP VERSION     DESCRIPTION                
1               Fri Feb  6 12:20:21 2026        superseded      xsy-chart-0.1.0 1.16.0          Install complete           
2               Fri Feb  6 12:34:10 2026        failed          xsy-chart-0.1.0 1.16.0          Upgrade "xsy-chart" failed: context canceled
3               Fri Feb  6 12:34:43 2026        superseded      xsy-chart-0.1.0 1.16.0          Rollback to 1              
4               Fri Feb  6 12:35:58 2026        deployed        xsy-chart-0.1.0 1.16.0          Upgrade complete           
```

#### 回退

回退到版本1

```
helm rollout xsy-chart 1 -n ai-deliver
```

执行结果

```
jcjy@jcjy-msi:~$ helm rollback xsy-chart 1 -n ai-deliver
Rollback was a success! Happy Helming!
```

history中会新增一个版本

```
jcjy@jcjy-msi:~$ helm history xsy-chart -n ai-deliver
REVISION        UPDATED                         STATUS          CHART           APP VERSION     DESCRIPTION            
1               Fri Feb  6 12:20:21 2026        superseded      xsy-chart-0.1.0 1.16.0          Install complete       
2               Fri Feb  6 12:34:10 2026        failed          xsy-chart-0.1.0 1.16.0          Upgrade "xsy-chart" failed: context canceled
3               Fri Feb  6 12:34:43 2026        superseded      xsy-chart-0.1.0 1.16.0          Rollback to 1          
4               Fri Feb  6 12:35:58 2026        superseded      xsy-chart-0.1.0 1.16.0          Upgrade complete       
5               Fri Feb  6 12:43:06 2026        deployed        xsy-chart-0.1.0 1.16.0          Rollback to 1 
```

#### 卸载

```
helm uninstall xsy-chart -n ai-deliver
```

就没有history了

```
jcjy@jcjy-msi:~$ helm history xsy-chart -n ai-deliver
Error: release: not found
```

#### 打包

```
helm package xsy-chart
```

运行结果

```
jcjy@jcjy-msi:~/xsy-project/helm$ helm package xsy-chart
Successfully packaged chart and saved it to: /home/jcjy/xsy-project/helm/xsy-chart-0.1.0.tgz
```

如果搭建了类似harbor的仓库就可以push



### 从仓库里下Chart

#### 添加仓库、搜索

```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm search repo bitnami/nginx

```

#### 看Chart但不安装

```
helm show values bitnami/nginx
```

或者直接 [charts/bitnami/nginx/values.yaml at main · bitnami/charts](https://github.com/bitnami/charts/blob/main/bitnami/nginx/values.yaml)

> value.yaml是参数字典

#### 最小化安装（先跑起来）

```
helm install nginx-lab bitnami/nginx
```

跑不起来...代理问题

```
jcjy@jcjy-msi:~$ helm install nginx-lab bitnami/nginx

Error: INSTALLATION FAILED: failed to perform "FetchReference" on source: Get "https://registry-1.docker.io/v2/bitnamicharts/nginx/manifests/22.4.7": dial tcp 128.121.243.107:443: i/o timeout
```







