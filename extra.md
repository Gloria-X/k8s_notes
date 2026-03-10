# minikube 搭建环境

minikube 是一个轻量级的 Kubernetes 发行版可以在本地运行单节点的 Kubernetes 集群。

kubectl 是一个命令行工具，可以通过在命令行输入各种命令与 Master Node 的 apiserver 交互，从而与 Kubernetes 集群进行交互。

1. 命令行输入`choco install minikube`安装 minikube
2. `minikube version`查看版本信息验证是否安装成功

如果出现类似下面的警告，那就自己到相应目录下新建一个文件

Unable to resolve the current Docker CLI context "default": context "default": context not found: open C:\Users\LittleGuai\.docker\contexts\meta\37a8eec1ce19687d132fe29051dca629d164e2c4958ba141d5f4133a33f0688f\meta.json: The system cannot find the path specified.

1. `minikube start`创建一个集群

下面这条命令先不加参数，直接启动如果很慢的话，试试指定镜像源为 cn，还是慢的话加上后面的版本参数，初步学习就不用追求最新版了。

```
minikube start --image-mirror-country='cn'  --kubernetes-version=v1.23.9
```

成功 start 之后就可以`sudo kubectl get nodes`查看集群中的节点信息了。

## K3s 和 Multipass

Win 安装 Multipass 之后要启动软件再重启命令行 再执行`multipass version`才能看到版本信息

```powershell
# 查看帮助
multipass help
multipass help <command>
# 创建⼀个名字叫做k3s的虚拟机
multipass launch --name k3s
# 在虚拟机中执⾏命令
multipass exec k3s -- ls -l
# 进⼊虚拟机并执⾏shell
multipass shell k3s
# 查看虚拟机的信息
multipass info k3s
# 停⽌虚拟机
multipass stop k3s
# 启动虚拟机
multipass start k3s
# 删除虚拟机
multipass delete k3s
# 清理虚拟机
multipass purge
# 查看虚拟机列表
multipass list
# 创建一台虚拟机
multipass launch --name k3s --cpus 2 --memory 4G --disk 10G
```

创建新的虚拟机之后由于不知道管理员密码无法进入管理员模式，就用 `sudo paswd root`重置密码再进入。

### 一个提升效率的准备工作

我们每次登录虚拟机时都得用`multipass shell hostname`命令，然后再输入密码，有点麻烦。

做点工作省略这些步骤。

先用`multipass shell hostname`登录到虚拟机中。

然后为 ubuntu 用户添加一个密码`sudo passwd ubuntu`（123456 就好）

对，没错，为了免密登录我们得先配置密码，出于安全考虑

然后修改 SSH 配置`sudo vi /etc/ssh/sshd_config`，把下面这三个都改为 yes

```powershell
PubkeyAuthentication yes
PasswordAuthentication yes
KbdInteractiveAuthentication yes
```

vi 编辑器技巧

1. 按 / 键进入搜索模式，输入待匹配字符串之后按回车，光标会跳到第一个匹配处，然后按 n 跳到下一个，N 跳到上上一个
2. 把光标移动到一个单词的开头，按 dw 可以删除整个单词
3. 按 i 进行编辑模式，编辑完按 Esc 退出编辑模式
4. 在普通模式下按 : 进入命令模式，输入 wq 保存退出

编辑好 SSH 配置文件之后要重启 SSH 服务`sudo service ssh restart`

做完上面这些工作之后就可以用 SSH 来登录虚拟机了，执行`ssh ubuntu@ip`命令后输入密码登录

说好的免密登录呢？别急，往下看

#### 配置免密登录

先了解一下原理——非对称加密，我们用自己的电脑生成一对公钥和私钥，私钥保存好，公钥发给各个虚拟机，这样就能通过匹配公钥和私钥进行登录而不用输入密码

![img](https://cdn.nlark.com/yuque/0/2024/jpeg/38959865/1713426756137-fec45e85-526b-466d-8302-9eb5f323d430.jpeg)

先用 ssh 生成一对公钥和私钥`ssh-keygen -t rsa -b 4096`，回车之后会提示为文件设置密码，建议直接回车不设密码

gen：generate，-t：type 密钥类型，-b：bit 位数

生成密钥后到当前用户下的 .ssh 目录下 `ls` 查看公钥和私钥的文件。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713345988227-966f5f09-8f23-4120-ac0b-563904bc40c0.png)

我们需要把公钥复制到虚拟机中，Linux 和 Mac直接执行`ssh-copy-id username@remote_host`就可以自动把本地的公钥复制到虚拟机中，然鹅，Windows 系统不支持这个命令，有两个办法可以解决。

ssh-copy-id 命令用于将本地计算机上的公钥添加到远程主机的 ~/.ssh/authorized_keys 文件中

1. 既然 Windows 不行那我们就找个 Linux，想想有Windows 上有什么是 轻量级 Linux 系统？GitBash，用 GitBash 进入到  **.ssh** 文件夹下，然后执行命令。需要你输入前面设置的密码。
2. ssh-copy-id 命令的本质是把本地的公钥添加到远程虚拟机的`~/.ssh/authorized_keys`文件里，PowerShell 行不通那就自己复制，把 `.ssh/id_rsa.pub` 的内容复制出来，到虚拟机中写入就好了。

#### 配置命令别名

每次都要输入`ssh hostname@ip`也是有点麻烦，我们给这个命令起个别名更方便一些

- Linux 和 MacOS 可以直接用 alias 直接给命令起别名，但 Windows 又没这个命令，得另外想办法。
  注意如果只是用命令`alias master='ssh ubuntu@ip'`起别名的话只是临时有效，想永久生效的话得把命令保存到`.bash_profile`文件中。（原理是保存到文件后每次打开终端都会加载这个别名）

Linux 优势之一

- Windows 先在命令行中输入`echo $PROFILE`，查看 PowerShell 配置文件的位置

```powershell
PS C:\Users\LittleGuai> echo $PROFILE
D:\文档\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
```

进入到 `D:\文档\WindowsPowerShell`文件夹下，新建一个文件命名为`Microsoft.PowerShell_profile.ps1`，用记事本打开输入命令别名，**保存关闭文件后重新开一个命令行**。

注意 multipass 创建的虚拟机重启之后会重新分配 IP，所以如果重启了虚拟机这里的 IP 也要跟着改。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713361342037-732cfd5e-bc33-4f97-883a-ea7044d24ee7.png)

如果遇到报错看看下面的[报错合集](https://www.yuque.com/xiaoguai-pbjfj/cxxcrs/ocefqltbmbgl5eqg#hfZe1)里有没有，没有就继续。

master 操作完之后 worker 也一样的操作，耐点心，后面会方便很多。

千辛万苦终于到了这里，现在终于可以轻松登录虚拟机了。

如果你输入别名后久久连不上，那就检查一下 IP 吧。

### K3s 创建集群

- 登录虚拟机后执行命令创建，这里用的是国内的镜像

```powershell
ubuntu@k3s:~$ curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | INSTALL_K3S_MIRROR=cn sh -
```

安装好之后`sudo kubectl get nodes`查看已有节点，这个是 **Master** 节点

```powershell
ubuntu@k3s:~$ sudo kubectl get nodes
NAME   STATUS   ROLES                  AGE   VERSION
k3s    Ready    control-plane,master   15m   v1.29.3+k3s1
```

- 在 Master 节点上获取 token，这个 token 是其它节点加入集群的凭证

```powershell
ubuntu@k3s:~$ sudo cat /var/lib/rancher/k3s/server/node-token
# 你自己的token
```

- 接下来添加环境变量 TOKEN 和 MASTER_IP

 Linux 和 Mac 用户执行这条命令

```
TOKEN=$(multipass exec k3s sudo cat /var/lib/rancher/k3s/server/node-token)
```

`TOKEN=`：这是声明一个名为 TOKEN 的变量。

`$(...)`：命令替换的语法，它会执行括号中的命令，并将其输出作为整个表达式的结果。

`exec` 是 multipass 命令的一个子命令，用于在指定的虚拟机实例中执行命令。

multipass exec k3s sudo cat /var/lib/rancher/k3s/server/node-token：指定 k3s 虚拟机执行`sudo cat /var/lib/rancher/k3s/server/node-token`

整个命令最终的结果就是把 node-token 文件里的值赋值给环境变量 TOKEN

然后执行`echo $TOKEN`查看变量值

Windows 用户执行这一条，这条命令的效果跟自己到系统变量里添加一个 TOKEN 变量是一样的，不想输命令就常规操作

```
[Environment]::SetEnvironmentVariable("TOKEN", $(Invoke-Expression "multipass exec k3s sudo cat /var/lib/rancher/k3s/server/node-token"), [System.EnvironmentVariableTarget]::Machine)
```

下面这条命令只会在当前会话中保持有效，关闭会话就消失了，了解即可

```
$env:TOKEN = Invoke-Expression "multipass exec k3s sudo cat /var/lib/rancher/k3s/server/node-token"
```

`$env:TOKEN`查看变量值

- 然后获取 Master 节点的 IP
  Linux/Mac：`MASTER_IP=$(multipass info k3s | grep IPv4 | awk '{print $2}')` 
  Windows：`[Environment]::SetEnvironmentVariable("MASTER_IP", $(Invoke-Expression 'multipass info k3s | Select-String "IPv4" | ForEach-Object { $_.ToString().Split(" ")[-1] }'), [System.EnvironmentVariableTarget]::Machine)`

这里注意 Invoke-Expression 后面用单引号，用双引号的话会与子命令的双引号匹配而提前结束命令

下面这条命令也只是设置临时变量，了解即可

```
$env:MASTER_IP = Invoke-Expression 'multipass info k3s | Select-String "IPv4" | ForEach-Object { $_.ToString().Split(" ")[-1] }'
```

获取后`$env:MASTER_IP`查看变量值

Windows 一般在设置完系统变量之后要**重新打开会话**载入变量

- 接下来就可以创建 Worker 节点了，我们创建两个 worker1 和 worker2

```
multipass launch --name worker1 --cpus 2 --memory 2G --disk 10G
```

如果在这里遇到报错`launch failed: Start-VM`，去下面找找，没有就跳过

创建完把两台工作机都[配置免密登录](https://www.yuque.com/xiaoguai-pbjfj/cxxcrs/ocefqltbmbgl5eqg#YSDPA)

- 给两台 Worker 安装 k3s 并设置环境变量

```bash
 for f in 1 2; do
     multipass exec worker$f -- bash -c "curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | INSTALL_K3S_MIRROR=cn K3S_URL=\"https://$MASTER_IP:6443\" K3S_TOKEN=\"$TOKEN\" sh -"
 done
```

Linux/Mac 用户直接执行，Windows 用户用 GitBash 执行，复制后在 GitBash 中 Shift+Insert 粘贴。

ToLearnL：这里我还没搞懂怎么在 PowerShell 上实现，有兴趣的同学可以试试下面这段，我用 GitBash 装好之后再执行这段就没反应了

```powershell
foreach ($f in 1, 2) {
  Invoke-Expression "multipass exec worker$f -- bash -c `"curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | INSTALL_K3S_MIRROR=cn K3S_URL=`"https://$MASTER_IP:6443`" K3S_TOKEN=`"$TOKEN`" sh -`""
}
```

PowerShell 中会解析双引号里的变量但不解析单引号里的，这里面带了 $f，所以得用双引号包裹，其他引号就得用反单引号 ` 转义

完成上面的工作之后登录 Master，执行`sudo kubectl get nodes`，就能看到集群信息了

```powershell
ubuntu@k3s:~$ sudo kubectl get nodes
NAME      STATUS   ROLES                  AGE   VERSION
k3s       Ready    control-plane,master   20h   v1.29.3+k3s1
worker1   Ready    <none>                 62m   v1.29.3+k3s1
worker2   Ready    <none>                 62m   v1.29.3+k3s1
ubuntu@k3s:~$
```

### kubectl 常用命令

#### 创建一个 Pod

```
sudo kubectl run podName --image=imageName
```

用这个命令创建一个 Pod 已经被弃用，并在较新版本的 Kubernetes 中不再建议使用，ToLearn：规范的操作方法

```powershell
ubuntu@k3s:~$ sudo kubectl run nginx --image=nginx
pod/nginx created
ubuntu@k3s:~$ sudo kubectl get pod
NAME    READY   STATUS              RESTARTS   AGE
nginx   0/1     ContainerCreating   0          5s
# 上面这个是正在创建的状态，创建完之后会变成 Running 
ubuntu@k3s:~$ sudo kubectl get pod
NAME    READY   STATUS    RESTARTS   AGE
nginx   1/1     Running   0          5m4s
```

也可以使用 creat 命令来创建想要的资源对象

`ubuntu@k3s:~$ sudo kubectl create -h`可以查看 create 命令相关的帮助文档

翻一翻可以看到，create 命令的资源对象里并没有 Pod，因为 Pod 是 Kubernetes 中最基本的资源对象，通常情况下我们并不会直接创建一个 Pod，而是创建一个 Pod 的上层资源对象

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713455440102-8b7a5b26-bee0-41e2-9190-d77b860ef191.png)

现在我们来创建一个 Deployment，`ubuntu@k3s:~$ sudo kubectl create deployment nginx-deployment --image=nginx`

电脑性能不是很好的话 `sudo kubectl get pod`查看 Pod 可能新建的 Pod 会一直是 ContainerCreating 状态，不着急，耐心等一下，只要没报错，它会 Running 的。

```powershell
ubuntu@k3s:~$ sudo kubectl get pod
NAME                                READY   STATUS              RESTARTS   AGE
nginx                               1/1     Running             0          137m
nginx-deployment-6d6565499c-xrkv9   0/1     ContainerCreating   0          2m31s
```

在 Deployment 和 Pod 之间还有一个中间层 ReplicaSet，用来管理 Pod 的副本数量，什么？副本？听着有点耳熟，看看前面对 [Deployment](https://www.yuque.com/xiaoguai-pbjfj/cxxcrs/ocefqltbmbgl5eqg#qnI4N) 的介绍，好像明白了什么。

`sudo kubectl get replicaset`查看 replicaset 列表，注意看，这里有个字符串有点眼熟，这个 replicaset 的 ID 在前面查看的 Pod 里出现过。Pod Name 分为三个部分，自己起的名字、replica ID、Pod ID，所以 Deployment、ReplicaSet 和 Pod 三者的关系就是 Pod Ⅽ ReplicaSet Ⅽ Deployment，通过 Pod Name 中的 ReplicaSet ID 就可以知道这个 Pod 属于哪个 ReplicaSet，ReplicaSet Name 里也包含所属 Deployment 的 Name。

```powershell
ubuntu@k3s:~$ sudo kubectl get replicaset
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-6d6565499c   1         1         0       3m20s
```

replica 就是副本的意思

ReplicaSet 并不用我们手动创建，而是通过 Deployment 来完成各种配置和管理。

#### 通过 Deployment 指定副本数量

`sudo kubectl edit deployment nginx-deployment`打开 Deployment 的配置文件，找到 replicas，把值改为 3。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713458116161-2009c593-cd30-45c7-8335-49325c1614c1.png)

退出后查看一下 Pod，可以发现多了两个副本

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713458174322-8facf34f-c698-421a-9e9a-9488264e2cf4.png)

这个方式不是很稳妥的方式，了解即可

# Kubernetes 调试命令和技巧

- 查看日志：`sudo kubectl logs podName`
- `exec`命令：以交互式的方式进入 Pod 中的一个容器，并启动一个 Bash shell。
  `sudo kubectl exec -it podName -- /bin/bash`

```powershell
ubuntu@k3s:~$ sudo kubectl exec -it nginx-deployment-6d6565499c-xrkv9 -- /bin/bash
root@nginx-deployment-6d6565499c-xrkv9:/#
```

kubectl exec：进入一个正在运行的 Pod 中执行命令。

-it：是下面两个选项的组合：

-i：允许你与Pod中的容器交互式地通信。

-t：为命令分配一个伪终端，使你能够使用命令行界面。

--：这个是一个分隔符，表示接下来的内容是要在容器内部执行的命令。

/bin/bash：这是要在容器内部执行的命令。在这个例子中，它启动了一个Bash shell。

## YAML 配置文件的使用

我们创建资源对象时可以通过指定各种参数来配置生成的资源对象的状态，比如`kubectl create deployment nginx-dep --image=nginx --replicaset=3`，这尊就指定了镜像是 nginx，副本数量是 3，但只在命令行中声明不方便我们日后查看，所以写到配置文件中更实用。

- 通过配置文件创建资源对象

先创建一个 yaml 文件`vi nginx-deployment.yaml`

```yaml
apiVersion: apps/v1  # 定义使用的API版本，这里是apps/v1，表示使用应用的v1版本API。
kind: Deployment  # 定义资源类型为Deployment，表示部署一个应用。
metadata:  # 元数据部分，用于描述Deployment的基本信息。
  name: nginx-deployment  # Deployment的名称为nginx-deployment。
spec:  # 规格部分，定义Deployment的规格。
  selector:  # 选择器部分，用于选择要管理的Pod。
    matchLabels:  # 匹配标签部分。
      app: nginx  # 匹配标签为app=nginx的Pod。
  replicas: 3  # 指定副本数为3，意味着会运行3个相同的Pod实例。
  template:  # 模板部分，定义创建新Pod时使用的模板。
    metadata:  # 模板的元数据部分。
      labels:  # 标签部分，为新创建的Pod定义标签。
        app: nginx  # 新创建的Pod的标签为app=nginx。
    spec:  # 新创建的Pod的规格。
      containers:  # 容器列表，定义在Pod中运行的容器。
        - name: nginx  # 容器的名称为nginx。
          image: nginx:1.25  # 使用的容器镜像是nginx:1.25。
          ports:  # 容器的端口配置。
            - containerPort: 80  # 容器监听的端口号为80。
```

然后`sudo kubectl create -f nginx-deployment.yaml`根据配置文件创建一个 Deployment

```yaml
ubuntu@k3s:~$ sudo kubectl create -f nginx-deployment.yaml
deployment.apps/nginx-deployment created
```

创建完查看一下效果，可以看到多出一个 Deployment 且副本数量为 3

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713511531852-c80a72ed-ddef-4bb0-b62c-5c8b1b9cae06.png)

也可以加上`-o wide`参数查看每个 Pod 的 IP

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713513219076-020a7a5b-2835-426a-9afb-88d55a652b1e.png)

上面的 IP 是集群内部的 IP，无法从集群外部访问

也可以通过配置文件删除资源对象`sudo kubectl delete -f nginx-deployment.yaml`，通过这个文件创建的**所有**资源对象都会被删除。

- 根据配置文件应用资源对象

```
sudo kubectl apply -f nginx-deployment.yaml
```

如果该文件对应的资源对象还没创建，则创建并启用资源对象，如果已经存在则更新后启用。

试试把上面的配置文件副本数量改为 2，然后再查看变化。

这就量使用配置文件来管理 Pod 的优势所在，遇到流量高峰的时候，修改一下副本数量就可以快速扩容，高峰过后也可以主很方便地释放资源。

甚至可以通过配置实现自动扩缩容，原理就是定时检查资源对象的状态，比较状态和配置是否一致，如果不一致就自动修改资源的状态，使其和配置保持一致

create 和 apply 的区别：类比创建虚拟机，create 只是创建但没有启用资源对象，apply 会创建/更新资源对象后启用。

## 使用 Service 提供外部服务

Pod 使用的是一个集群内部的 IP 地址，如果用 Pod 来运行 nginx 是无法从集群外部访问到页面的。比如上面创建的 Pod，在 Master 节点上执行`curl ip`就可以访问到 nginx 页面。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713513831512-dca57ae7-df07-418f-ad2a-020630d7952a.png)

但 `exit 退出到 PowerShell 后就无法访问了。`

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713513936812-a5c59c61-f0d8-4cb4-90dd-0b3730ce985a.png)

另一个问题就是 Pod 并不是一个稳定的实体，经常会被创建或销毁，这里它的 IP 地址也会发生变化。

解决方案就是**使用 Service 来提供外部服务**。

- 创建一个 Service `sudo kubectl service nginx-service`
- 也可以直接将已存在的 Deployment 对外公开为一个服务
  `sudo kubectl expose deployment nginx-deployment`

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713514595605-708e8e18-a9c2-4ea9-8538-d84bd748b7b2.png)

- 查看资源详细信息`sudo kubectl describe [资源类型] [资源名称]`

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713514735064-af041955-6603-4b52-abf5-c2384e986d53.png)

- 通过配置文件创建 Service

新建一个配置文件 nginx-service.yaml

```yaml
apiVersion: v1  # 使用的Kubernetes API版本，这里是v1。
kind: Service  # 定义资源类型为Service，表示创建一个服务。
metadata:  # 元数据部分，用于描述Service的基本信息。
  name: nginx-service  # Service的名称为nginx-service。
spec:  # 规格部分，定义Service的规格。
  selector:  # 选择器部分，用于指定服务应该选择哪些Pod作为后端。
    app: nginx  # 选择具有标签app=nginx的Pod作为后端。
  ports:  # 端口配置，定义Service暴露的端口。
    - protocol: TCP  # 使用TCP协议。
      port: 80  # Service暴露的端口号为80。
      targetPort: 80  # 转发到后端Pod的端口号也为80。
```

这里需要先了解一下选择器 selector  的作用：选择特定的资源，一般和 label 标签一起使用，类似 CSS 的选择器，我们前面在创建 Deployment 时已经给 Deployment 绑定了一个选择器，回头看看[配置文件](https://www.yuque.com/xiaoguai-pbjfj/cxxcrs/ocefqltbmbgl5eqg#svFr9)里的 matchLabels，也可以`sudo kubectl describe deployment nginx-deployment`看一下 Deployment 信息，可以看到 Deployment 信息下有个 Selector

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713518081375-4571115e-9dc7-4dab-8b7b-5d6db27c58ff.png)

然后再看看 Pod 信息，创建的三个 Pod 都有 Labels 标签

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713517657862-41ca07ef-1ffb-4c13-ac96-09d510716de9.png)

总结一下就是，在 Deployment 声明一个选择器，在 Pod 里贴上一个标签，选择器与标签匹配的 Deployment 就可以管理 Pod。



保存配置文件后应用一下这个文件`sudo kubectl apply -f nginx-service.yaml`

但是这个服务还是一个集群内部的服务，无法从集群外部访问，这时我们就得用到 NodePort 类型的服务。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713519424716-14967802-227d-40fa-bc32-3cfc4b96aeaa.png)

NodePort 可以将服务公开到集群的节点上，然后我们通过 IP 和端口就可以访问到服务了。

我们创建 Service 时没有指定服务的类型，那这个 Service 默认就是一个 ClusterIP 类型的服务，也就是集群内部的服务，现在我们来将 Service 的服务类型改为 NodePort，只要在配置文件里加上 type 和 nodePort 就好了。注意端口的范围在 30000~32767 之间（这个范围是由 Kubernetes 团队选择的，因为它们通常不会被其他应用或服务占用）

```yaml
apiVersion: v1  # 使用的Kubernetes API版本，这里是v1。
kind: Service  # 定义资源类型为Service，表示创建一个服务。
metadata:  # 元数据部分，用于描述Service的基本信息。
  name: nginx-service  # Service的名称为nginx-service。
spec:  # 规格部分，定义Service的规格。
  type: NodePort	# 指定服务类型
  selector:  # 选择器部分，用于指定服务应该选择哪些Pod作为后端。
    app: nginx  # 选择具有标签app=nginx的Pod作为后端。
  ports:  # 端口配置，定义Service暴露的端口。
    - protocol: TCP  # 使用TCP协议。
      port: 80  # Service暴露的端口号为80。
      targetPort: 80  # 转发到后端Pod的端口号也为80。
      nodePort: 30080
```

保存后 apply 一下，`sudo kubectl apply -f nginx-service.yaml`

然后查看 Service 信息，可以看到服务类型变成了 NodePort，且端口号为 30080

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713528303649-e14a3a22-c17c-4722-ad34-58bc1f99a579.png)

查看一下 IP 地址`sudo kubectl get nodes -o wide`

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713528365445-8cfdd4d6-a5c8-4afb-97d7-cf8e7c0f3a25.png)

然后打开浏览器，输入 `nodeIP:port`，可以访问了！

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713528797154-ca2b1ce9-b2c7-4e3a-a487-e0028a1a11d7.png)

关于 Service 的类型还有其它各类和应用，LoadBalcancer、ExternalName、Headless，感兴趣上官网了解一下

# 可视化 Kubernetes  管理工具

工具叫 Portainer，只需要在官网上下载一个配置文件，然后 apply 这个文件就好了。

那么问题来了，我们用 Windows 下载的文件怎么上传到虚拟机？

使用`scp`命令`scp \path\of\your\file username@ip:/dir`

如果是直接复制到根目录可以`scp \path\of\your\file ubuntu@172.22.94.170:`注意冒号不能省

有了配置文件后执行`sudo kubectl apply -n portainer -f portainer.yaml`

注意这里有个`-n portainer`参数，-n 用来指定命名空间

n 代表 Namespace，命名空间，一种将 Kubernetes 资源进行分组的机制，相当于把一个 Kubernetes 集群划分成多个空间，不同的项目或团队可以在各自的空间上独立工作互不干扰，不同命名空间中的资源也可以同名。

适用于多租户环境（又学一个高级词），突然反应过来云服务器是怎么运行的了，把一个节点划分多个 Namespace，然后就可以租给多个用户了

如果看教程看入迷了，启动了 portainer 之后过了五分钟没登录的话，再去浏览器访问 portainer 会收到提示 Your Portainer instance timed out for security purposes. To re-enable your Portainer instance, you will need to restart Portainer. 这时候要重启服务，直接重新 apply 一下就好了`sudo kubectl apply -n portainer -f portainer.yaml`，但这样还是得每五分钟去弄一下它。找到一个一劳永逸的方法。改一下 portainer.yaml 文件的检查周期`livenessProbe.periodSeconds`，改完记得重新 apply 一下。

```yaml
livenessProbe:
  httpGet:
    path: /
  periodSeconds: 3600  # 修改这里的值，单位为秒，比如修改为600表示每10分钟检查一次
```

这样改完就是每一小时检查一次活跃了。界面如下。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713535904965-029832f0-924f-403b-97bb-f20d1642177b.png)

##  报错合集

#### launch failed: Remote "" is unknown or unreachable.

我没猜错的话你的电脑里有梯子，而且你科学上网了，出现这个报错就说明连不上远程，你开梯子的时候会修改 host 文件，导致 multipass 连接 Remote 的时候无法正确 IP，用火绒的网络诊断工具诊断并修理一下就好了。

#### ubuntu@ip: Permission denied (publickey)

确保 sshd 配置文件里以下三个选项都是 yes

```powershell
PubkeyAuthentication yes

# To disable tunneled clear text passwords, change to no here!
PasswordAuthentication yes

# Change to yes to enable challenge-response passwords (beware issues with
# some PAM modules and threads)
KbdInteractiveAuthentication yes
```

#### Bad permissions. Try removing permissions for user: \\Everyone (S-1-1-0) on file C:/Users/LittleGuai/.ssh/id_rsa.

我不是配置了免密登录了吗？怎么还要输入密码？别急，读一下报错信息。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713362112233-18f60762-3985-423f-b33e-fcbd56fee967.png?x-oss-process=image%2Fcrop%2Cx_0%2Cy_0%2Cw_1220%2Ch_337)

这个报错是因为本地私钥的文件权限放得太开了（too open）， 要求私钥文件只能由当前用户访问。

先用 `$env:username`查看当前用户名，记住这个用户名，后面有用

```powershell
PS C:\Users\LittleGuai> $env:username
姚小怪
```

进入`C:\Users\LittleGuai\.ssh`按下面操作，这里的所有者（Owner）就是文件的创建人，主体（Principal）就是可以访问私钥文件的用户，就是因为可访问的用户太多所以系统认定这个文件不安全，所以要把主体全部删掉（或者可以尝试禁用他们的权限），这样被删掉的主体就访问不了文件了。

再把所有者改为当前用户（如果跟前面查到的一样可以不用改），主体中添加当前用户就可以了。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713362581350-a1539acc-1866-438e-908b-d66776a228fe.png)

6 不见了，别在意，下面是更改所有者的操作，添加主体点左下角的“添加”，一样的操作。

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713362862557-4a6f05cb-b3b1-49b5-9a4c-09bc71e83592.png)

最终结果就是所有者和主体都只有你自己

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713368183827-2d2369c8-04f8-4e94-b4b1-830bdfa7ac28.png)

然后就可以快乐地去用别名登录虚拟机了。

#### launch failed: Start-VM

报错信息如下

```powershell
+ CategoryInfo          : NotSpecified: (:) [Start-VM], VirtualizationException
+ FullyQualifiedErrorId : Unspecified,Microsoft.HyperV.PowerShell.Commands.StartVM
```

打开任务管理器看看内存占多少了

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713417261493-25ee5cc2-6fce-476c-8b25-388f5480e35b.png)

再看看你新建虚拟机的时候指定多大的内存，这时候应该都不够了，因为 Master 的内存就占了 8G，所以得先关掉 Master 释放内存再新建 Worker。

内存不够的话我们就将就一下不要创建那么大内存的虚拟机了，改成 4G 好了。

可以直接在 PowerShell 用命令改，先关掉虚拟机`multipass stop k3s`，再改内存`multipass set local.k3s.memory=4G`，再启动虚拟机`multipass start k3s`，最后查看虚拟机信息`multipass info k3s`，没意外的话 Memory usage 应该改好了。

Windows 也可以用 Hyper-V 改，win+s 搜索 Hyper-V，不用关机就能直接改（咱 Windows 用户也扬眉吐气一回）

![img](https://cdn.nlark.com/yuque/0/2024/png/38959865/1713418609900-d67403d3-d31a-4b65-8c7c-da352d8d5933.png)

# Windows PowerShell 下常用命令

注意：PowerShell 和普通的 cmd 不一样，命令也不一样

列出环境变量：`Get-ChildItem Env:`

查看某个环境变量值：`$env:变量名`