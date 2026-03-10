[About Calico | Calico Documentation](https://docs.tigera.io/calico/latest/about/?spm=5176.28103460.0.0.b2e87551DX3Jw1)



flannel 二层

podA <-网桥cni0-> podB

calico 不在同一个子网下，需要跨路由 纯三层

podA <-router-> podB







## 知识补课

### Kubernetes networking basics

每个pod都有自己的IP地址

任何节点上的pod都可以与其他节点上的pods进行通信，无需NAT（源IP是pod A的真实 IP，不是node1的IP）

要做到跨节点无 NAT 通信，底层网络必须：

- 要么 **支持三层路由**（如 Calico BGP）
- 要么 **用 overlay 封装**（如 Flannel VXLAN、Calico IPIP）
- 要么 **云平台帮忙配路由**（如 AWS VPC + kubenet）

### CNI plugins

CNI插件是个标准的API，有两种类型

- CNI network plugins：负责在pod网络中新增删除pod，包括创建、删除每个pod的网络接口，以及其他和网络相关的内容（创建 veth pair、挂到 bridge/路由表、设置 namespace 网络栈）
- CNI IPAM Plugin：从地址池分配IP、记录分配状态、回收IP

1. kubelet 调用 CNI 配置（如 /etc/cni/net.d/10-calico.conflist）
2. CNI 配置指定：先用 calico（network plugin），再用 calico-ipam（IPAM plugin）
3. calico-ipam 从 Calico 的 IPPool 中分配一个 IP
4. calico 插件创建 veth，设置路由，写入 iptables 策略

```
{
  "name": "k8s-pod-network",
  "cniVersion": "0.3.1",
  "plugins": [
    {
      "type": "calico",          // ← Network Plugin
      "log_level": "info",
      "datastore_type": "kubernetes",
      "nodename": "...",
      "ipam": {                  // ← 内嵌 IPAM Plugin
        "type": "calico-ipam"
      }
    }
  ]
}
```



### Cloud provider integrations

“云厂商集成”是一组专门针对某个云平台（比如 AWS）开发的控制器（controller），它们能自动配置该云平台底层的网络设施（比如 VPC 路由表）

云控制器（Cloud Controller Manager）会：自动在 VPC 中添加路由规则，告诉云网络：“去 Pod CIDR X.X.X.X/16，请走 Node Y”

【重点】例子：

假设有 2 个 EC2 实例（Node A 和 Node B）

- Node A 上的 Pod 使用 CIDR 10.244.1.0/24
- Node B 上的 Pod 使用 CIDR 10.244.2.0/24

如果用的是最简单的 CNI 插件（比如 kubenet，它本身不处理跨节点路由），那么默认情况下，Node A 不知道怎么把包发给 10.244.2.0/24；这时候，Cloud Controller Manager（CCM） 就会介入：

- 它检测到每个 Node 的 Pod CIDR（Classless Inter-Domain Routing）

  > k8s会把大网段细分给每个节点 10.244.1.0/24, 10.244.2.0/24...
  >
  > 用处：确保每个pod在集群内有唯一IP；知道某个IP属于哪个节点

- 自动在 AWS VPC 的路由表里加一条规则：“目标：10.244.2.0/24 → 下一跳：Node B 的私有 IP”

这样，即使你的 CNI 很简单（比如 kubenet），只要底层云网络知道“去哪个 Pod 网段要走哪台机器”，跨节点通信就能工作！

---

Calico 通常不需要依赖云路由，因为它自己通过 BGP 或 IPIP 实现了路由。但在某些混合场景下可共存

- **BGP 模式**：让每台 Node 像路由器一样，互相广播“我负责哪些 Pod 网段”。
- **IPIP 模式**：如果 BGP 不可用（比如在公有云上不支持自定义路由），就用 IP-in-IP 封装，在节点间打隧道

 Calico 一般不需要云平台帮你加 VPC 路由，因为它自己搞定了

但有些场景可能混合使用（比如部分节点用 Calico，部分用其他方案），或者为了简化网络策略，也可以让 Calico 和云路由共存（不过要小心冲突）



### Kubenet

k8s内置的兜底CNI，可以在本机创建cbr0 bridge，用host-local IPAM分配IP，但不能处理跨节点通信（必须使用云平台路由才能跨节点）

和calico不兼容，因为两者都想接管pod网络

- kubenet用cbr0 bridge
- calico用veth_路由表（或IPIP tunnel）

同时启用会导致网络混乱，因为两个CNI都要配置pod接口

用calico就不要开kubenet，部署k8s时设置--network-plugin=cni（而不是默认的kubenet）

Calico 默认 不启用 Overlay（纯 BGP 路由），但提供 IPIP/VXLAN 作为选项



### Overlay networks

叠加在底层网络之上的虚拟网络，把podIP包装进nodeIP的外层包中，常见协议：VXLAN、IP-in-IP (IPIP)

Calico 默认不启用 Overlay（纯 BGP 路由），但提供 IPIP/VXLAN 作为选项



什么情况下需要overlays

- 在 AWS 中，EC2 实例默认**只能与同子网实例二层通信**
- 跨子网流量必须经过 **VPC 路由表 + 路由器（如 AWS VPC Router）**
- 但很多企业网络或云环境**禁止自定义 IP 流量**（只允许本机 IP 作为源）

> 🔥 关键限制：**底层网络设备（交换机/路由器/安全组）可能丢弃“源 IP 不是本机”的包**





❗重要

BGP 让每个节点（Node）像路由器一样，互相“广播”自己负责哪些 Pod 网段；整个集群形成一个扁平的三层（L3）可路由网络，Pod IP 在物理网络上天然可达

Calico 默认（在支持的环境下）使用 纯三层路由（L3 Routing） + BGP 协议

1. 每个 Node 被分配一个 Pod CIDR 子网

   - 比如：Node A → `192.168.1.0/24`，Node B → `192.168.2.0/24`

2. Calico 在每个 Node 上运行一个 BGP 客户端（通常是 `bird` 或 `FRR`）

   这个客户端会：

   - 宣告：“我（Node A）负责 `192.168.1.0/24` 这个网段”
   - 从其他节点学习：“Node B 负责 `192.168.2.0/24`”

3. 节点之间建立 BGP 邻居关系

   可以是：

   - **Node-to-Node Mesh**（每台 Node 和所有其他 Node 直接建 BGP 连接）→ 小规模集群
   - **通过 Top-of-Rack (ToR) 交换机做路由反射器** → 大规模生产环境

4. **Linux 内核路由表自动更新**

   在 Node A 上执行 

   ```
   ip route
   ```

   会看到类似

   ```
   192.168.2.0/24 via <Node-B-IP> dev eth0
   ```

   这意味着：发往 `192.168.2.0/24` 的流量，直接走物理网络发给 Node B

5. Pod 发包时，无需封装

   - Pod1（192.168.1.5） → Pod2（192.168.2.10）
   - 数据包从 Pod1 出来 → 经过 veth 到 Node A → 查路由表 → 直接发给 Node B 的物理 IP
   - Node B 收到后，根据本地路由交给对应 Pod

> 没有隧道封装，是真正的**原生三层路由**



BGP模式依赖底层网络满足

| 条件                 | 说明                                                         |
| -------------------- | ------------------------------------------------------------ |
| ✅ 节点之间三层互通   | 所有 Node 的 IP 必须能互相 ping 通（通常默认满足）           |
| ✅ 允许自定义路由传播 | 物理网络设备（或云平台）必须允许节点之间学习/添加路由        |
| ❌ 公有云限制         | AWS/GCP/Azure 默认不允许虚拟机自行添加 VPC 路由（安全策略），所以 BGP 模式在公有云通常不能直接用 |

因此，在 **公有云上，Calico 默认会启用 IPIP 模式**（Overlay），绕过云平台的路由限制。
而在 **私有数据中心或裸金属环境**，如果网络设备支持 BGP（比如用 Cumulus、Arista、华为/华三交换机），就可以用纯 BGP 模式，性能更优



### Cross-subnet overlays（Calico 特色功能）

在子网内不封装，跨子网才封装

同一子网内，不封装 ≈  纯三层路由（网络层，IP地址路由）

跨子网，封装（IPIP/VXLAN），有开销

> 比全Overlay更高效





#### 如何判断“是否同子网”

判断发生在「源节点（Node A）的 Linux 内核路由查找阶段」

Calico 通过 预先配置好的内核路由表 + IPIP/VXLAN 的策略路由，让系统在查路由时自动决定是否走隧道接口（如 tunl0）；“是否同子网”的依据，是 目标 Node 的 IP 地址是否与本机在同一个 IP 子网（L3 子网）中 —— 这个信息来自 Calico 的 BGP 或节点拓扑感知

需要在 Calico 的 ippool 配置中启用

```
apiVersion: crd.projectcalico.org/v1
kind: IPPool
metadata:
  name: default-pool
spec:
  cidr: 10.244.0.0/16
  ipipMode: CrossSubnet   # ← 关键！也可以用 vxlanMode: CrossSubnet
  natOutgoing: true
```

Calico 会读取每个 Node 的 status.addresses（通常是 InternalIP），并根据这些 IP 所属的子网做判断

> 💡 例如：
>
> Node A: `192.168.10.5/24`
>
> Node B: `192.168.10.6/24` → **同子网** → 不封装
>
> Node C: `192.168.20.5/24` → **跨子网** → 封装

#### 流量路径示例

Node A 上运行了 Calico，它已经通过 BGP 或 API Server 获取了全集群的 “哪个 Node 负责哪个 Pod CIDR” 的映射，并写入了本地路由表

##### 同子网（无封装）

calico添加的路径可能是

```
10.244.2.0/24 via 192.168.10.6 dev eth0
```

走物理网卡eth0

```
PodA (10.244.1.5) 
→ Node A (192.168.10.5) 
→ 直接路由 → Node B (192.168.10.6) 
→ PodB (10.244.2.10)
```

路由表中有 `10.244.2.0/24 via 192.168.10.6`

零封装，零性能损失

##### 跨子网（IPIP封装）

calico

```
10.244.3.0/24 via 192.168.20.5 dev tunl0
```

注意：这里下一跳设备是 tunl0（IPIP 隧道接口），而不是 eth0

```
PodA (10.244.1.5) 
→ Node A 封装：[外层 IP: 192.168.10.5 → 192.168.20.5] + [内层: PodA → PodC]
→ 物理网络传输
→ Node C (192.168.20.5) 解封装
→ 交给 PodC (10.244.3.10)
```

自动将原始 IP 包（PodA → PodC）**交给 `tunl0` 接口处理**

tunl0是一个虚拟隧道设备，它会：

- 把原始包作为 **内层 payload**
- 加上新的 IP 头：源 = `192.168.10.5`，目的 = `192.168.20.5`
- 协议号设为 `4`（IPIP）

有轻微 CPU 和 MTU 开销（通常 MTU 设为 1480）

> ❗ “是否封装”的决策点，就在 ip route 查找结果中指定的出口设备是 eth0 还是 tunl0



---

本地 + 未来上云比较适合 IPIP Cross-Subnet模式

| 场景                       | 表现                                                 |
| -------------------------- | ---------------------------------------------------- |
| 当前（本地物理机，同子网） | ✅ 不封装，走纯三层路由，性能接近纯 BGP               |
| 未来（上阿里云，跨可用区） | ✅ 自动启用 IPIP 封装，绕过阿里云路由限制，保证连通性 |
| 混合部署（本地 + 云）      | ✅ 本地节点间直通，本地 ↔ 云节点走隧道，智能切换      |
| 运维                       | 🛠️ 只需一套 Calico 配置，无需变更                     |

Calico IPPool 推荐配置

```
apiVersion: crd.projectcalico.org/v1
kind: IPPool
metadata:
  name: default-ipv4-ippool
spec:
  cidr: 10.244.0.0/16
  ipipMode: CrossSubnet     # ← 关键！
  vxlanMode: Never          # 不用 VXLAN
  natOutgoing: true
  disabled: false
```

⚠️ 注意：
确保你的 Pod CIDR（如 10.244.0.0/16）不与 Node 所在网络冲突
在阿里云上，Node IP 是 VPC 内网 IP（如 172.16.x.x），Calico 能自动识别子网边界

阿里云上：

继续使用同一份 Calico 配置（只需调整 CIDR 避免冲突）
阿里云 ACK 默认使用 Terway 或 Flannel，但你可以 自定义安装 Calico
节点分布在不同 AZ（如 vsw-a, vsw-b）→ 自动触发 IPIP 封装
同一 AZ 内节点 → 依然无封装，高性能



但Calico Cross-Subnet本身不支持本地pod连通阿里云的pod

支持跨节点的pod连通，但节点必须是同一个k8s集群



### Pod IP routability outside of the cluster

区分“封闭集群” vs “开放网络集成”的核心指标

#### 不可路由（Overlay模式典型特征）

出向流量（pod --> 外部）

- 自动SNAT：源IP从podIP --> nodeIP
- 外部服务看到的是node，不是pod，日志审计很难追踪到具体pod

入向流量（外部 --> pod）

- 只能通过service/ingress
- 无法直接 `curl <podIP>`从集群外部访问

> 大多云上应用、安全隔离要求高的环境

#### 可路由（非Overlay+BGP模式）

出向：podIP直接出现在网络中，无SNAT

入向：外部设备可直接访问podIP（只要路由可达+防火墙放行）

**✅ 优势**

- 符合pod as vm的k8s网络立项模型

- 便于传统系统集成（白名单、审计）

- 简化调试（tcpdump可以看到真实源IP）

**❌挑战**

IP地址规则复杂

- 多个集群不能用相同的pod CIDR
- 企业内网可能已有IP冲突

依赖底层网络支持

- 本地数据需配置BGP路由器
- 公有云通常不开放BGP

> 强管控网络、混合云、需要直连pod的高性能计算



### BGP

BGP（Border Gateway Protocol）是互联网级路由协议，Calico 内置支持 BGP

#### calico如何使用BGP

1. 每个 Node 上的 **Felix + BIRD** 组件作为 BGP Speaker
2. 向邻居（其他 Node 或 ToR 交换机）宣告：“我这里有 `192.168.10.0/24` 的 Pod”
3. 物理网络学到路由后，可直接转发到对应 Node

#### 两种BGP模式

| 模式                 | 描述                                     | 适用环境            |
| -------------------- | ---------------------------------------- | ------------------- |
| Node-to-Node Mesh    | 所有 Node 互相建立 BGP 对等              | 小集群（<100 节点） |
| Route Reflector (RR) | 指定几个 RR 节点，其他 Node 只和 RR 通信 | 大规模集群          |





## About Calico Networking

Calico’s flexible modular architecture for networking includes the following.

### Calico CNI network plugin









## 💡Calico如何处理流量

### 【先了解下什么是ARP】

ARP（Address Resolution Protocol，地址解析协议） 是 IPv4 网络中用来 把 IP 地址转换成 MAC 地址 的协议

假设podA IP是 10.244.1.5，想发包给同子网的podB（10.244.1.6），但在二层（数据链路层）需要知道目标的MAC地址，podA就会广播一个ARP请求“10.244.1.6在谁那边，告诉我一下MAC”，理论上拥有该IP的设备podB就会用自己的MAC回应

### ❓但 Calico 的网络模型特殊在哪里

Calico 默认使用 “三层路由（L3 routing）” 模型，不依赖 overlay 网络（如 VXLAN），pod IP 是直接可达的，就像物理机一样

但在k8s的节点上：每个pod实际通过一个veth pair（虚拟网卡）连接到主机，pod的一端叫eth0，主机的一端叫calixxxx，pod的IP配置在pod自己的网络命名空间里，不在主机的主接口上，这就带来一个问题：如果pod发出ARP请求（比如问同网关或同节点其他pod的MAC），谁来回答

### 【继续补点课】

#### 网络命名空间

linux提供的一种隔离机制，可以想象成独立的小电脑，有自己的网卡（比如eth0）、IP地址、路由表、ARP表、防火墙规则（iptables）

每个pod在创建时，k8s会为它创建一个独立的网络命名空间，这样podA和podB虽然跑在一台物理机上，但彼此“看不见”对方的网络设备，就像在两台不通的电脑上一样

> “pod的IP配置在pod自己的网络命名空间里” 意思是：这个 IP 只在这个 Pod 的“小世界”里有效，主机主接口（比如 eth0）上并没有这个 IP



#### 虚拟网卡是CNI插件创建的，不是kubelet创建的

kubelet发现要启动一个新的pod时会调用CNI插件（如Calico）来“配置网络”，Calico创建一对veth pair（virtual ethernet pair）

- 一端叫 eth0，放进 pod的网络命名空间 → pod里看到的就是 eth0
- 另一端叫 caliXXXX（Calico 的命名习惯），留在主机的网络命名空间里

这两端像一根“虚拟网线”连在一起：从 pod的 eth0 发出的数据，会立刻出现在主机上的 caliXXXX 接口上，反之亦然（因为实际pod用的也是宿主机的资源）

---

网络命名空间隔离虽然默认不互通，但可以通过主机上的网络设施（veth+路由/网桥）让它们互通

```
Pod A (ns)        Host (root ns)         Pod B (ns)
   |                   |                    |
 eth0 <-----> cali12345|cali56789 <-----> eth0
                       |
                   (Linux 内核网络栈)
```

虽然每个pod有独立的网络命名空间，但它们都通过veth pair连到了主机上，只要

- IP路由表中有对应的条目
- 内核开启了IP转发（net.ipv4.ip_forward=1）

主机内容就知道如何把从cali12345进来的包，转发给cali56789



### Calico是怎么做到的

在主机上做了两件事情

1. 为每个pod的IP添加一条“直连路由”

   ❗❗❗❗❗这个是主机的路由表（nodeA），pod内部还有一个自己的路由表

   ```
   $ ip route
   10.244.1.2 dev cali12345 scope link
   10.244.1.5 dev cali56789 scope link
   ```

   意思是：要去10.244.1.2直接从cali12345接口发；要去10.244.1.5走cali56789

   > 不需要网关，也不需要ARP广播到整个局域网

2. 开启IP转发

   k8s节点默认会开启

   ```
   sysctl net.ipv4.ip_forward
   # 输出：net.ipv4.ip_forward = 1
   ```

   表示允许linux主机当中间人，帮不通接口之间的流量进行转发



### Flannel是怎么做的

创建一个cni0网桥

所有pod的veth另一段都插到cni0上，cni0就像个虚拟交换机，pod之间的通信就像接在同一个交换机上，这时会用到ARP，但因为都在同一个网桥广播域里，ARP都能正常工作



### 💡calico流程

#### podA --> podC（跨node）完整流程 IPIP

##### **step1**：podA发包（在pod自己的namespace）

```
dst = 10.244.3.10
```

pod内部路由表

```
default via 169.254.1.1 dev eth0
```

> pod只知道自己是10.244.3.10，要把所有的非本地流量都交给eth0
>
> 169.254.1.1是 pod eth0 对端 veth 在 pod namespace 里伪装出来的“网关 IP，不是pod，不是node，不是caliXXX，只是个钩子，让pod的IP栈“愿意把包发出去”

###### 【再理解下169.254.1.1存在的作用】

是一个“由主机代理响应的虚拟 IP”，它的“存在”完全依赖 proxy_arp

```
Pod ns:      eth0 (10.244.1.5)  ← 默认网关设为 169.254.1.1
              ↑
              | （Pod 认为这个 IP 就在 eth0 这一端）
              |
              | ← 虚拟网关钩子（169.254.1.1）
              |
              | veth pair
              |
Host ns:  caliXXXX （没有 IP 地址！）
```

> 🔸 关键点：caliXXXX 接口在主机上通常是没有 IP 地址的！只是个“通道”，不参与三层通信

pod发现不知道169.254.1.1的MAC会触发ARP请求，说“谁有169.254.1.1？”

ARP请求通过eth0发出，到达主机的caliXXX接口，主机内核看到这个ARP请求，发现目标IP是169.254.1.1

- 虽然caliXXX没配这个IP
- 但calico启用了proxy_arp（代理ARP）

```
cat /proc/sys/net/ipv4/conf/caliXXXX/proxy_arp
# 输出：1
```

主机代答ARP说："我是169.254.1.1，我的MAC是caliXXX的MAC"

pod收到回复后就把169.254.1.1的MAC存入ARP表，以后所有发往外部的包都直接发给这个MAC（实际进入主机）

---

最后！：包从 podA→ veth → caliXXXX（进入node）

##### **step2**：node收到包（第一次路由决策）

node查主路由表 CIDR

```
10.244.3.0/24 via 192.168.20.5 dev tunl0
```

这个包不是发给某个pod的，是要跨节点发给nodeC的 --> 交给tunl0

> tunl0本身代表的是这个目的网段需要IPIP封装
>
> 在 Calico 的默认设计里：
>
> - 同 Node：不走 tunl0
> - 同 L2 子网：不走 tunl0
> - 跨 L3 子网：走 tunl0

以上内容表明：去 10.244.3.0/24，需要先IPIP封装，外层下一跳是192.168.20.5

> 这条路由物理机下是BGP，云/无法跑BGP是api server加的
>
> linux只知道目的网段 --> 出口设备

##### **step3**：tunl0干活儿（封装）

tunl0做得事情不是“路由”，而是

```
外层 IP: 192.168.10.5 → 192.168.20.5
内层 IP: 10.244.1.5 → 10.244.3.10
```

> tunl0是一个“虚拟的三层隧道设备”，职责不是发包，而是在包外面再套一层IP头，像一个function

路由说dev tunl0时，linux内核会做

1. 把原始IP包（10.244.1.5 → 10.244.3.10）当payload

2. 新建一个外层IP头

   ```
   src = 192.168.10.5（本 Node 的 nodeIP）
   dst = 192.168.20.5（对端 Node 的 nodeIP）
   protocol = 4 (表示IPIP)
   ```

​	得到一个新的IP包

```
[外层: 192.168.10.5 → 192.168.20.5]`
`└── [内层: 10.244.1.5 → 10.244.3.10]
```

3. 封装完成后，再对“外层IP”做一次路由查找（封装完后，外层包还要再走一次路由）

​	内核现在要发送的是 192.168.10.5 → 192.168.20.5，于是

```
ip route get 192.168.20.5
# 输出：192.168.20.5 dev eth0 src 192.168.10.5
```

所以外层包会从 物理网卡 eth0 发出去（然后把包丢给eth0）Ethernet以太网

> tunl0 不是终点，它只是一个“中间处理函数”

最终包结构

```
[ Ethernet Header ]
  dst MAC: 网关或 Node C 的 MAC
  src MAC: Node A 的 eth0 MAC

[ Outer IP Header ]
  src IP: 192.168.10.5   ← Node A 的物理 IP
  dst IP: 192.168.20.5   ← Node C 的物理 IP
  protocol: 4 (IPIP)     ← 关键！表示 payload 是 IP：IPIP --> IP over IP

[ Inner IP Packet (original) ]  ← 这就是 payload
  src IP: 10.244.1.5     ← Pod A
  dst IP: 10.244.3.10    ← Pod C
  protocol: ICMP/TCP/etc.
```

总共有两层 IP 头：外层用于物理网络路由，内层是真正的 Pod 通信

##### **step4**：nodeC收到包，解封装

- nodeC的eth0收到外层包（192.168.10.5 → 192.168.20.5）

- 内核发现协议是4（IPIP），且本机有tunl0设备（IPIP隧道设备）

  > = 4 表示“外层 IP 包的 payload 是一个完整的 IP 包”，也就是使用了 IPIP 封装
  >
  > 由[Protocol Numbers](https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml)维护

- 自动将内层包（10.244.1.5 → 10.244.3.10）提取出来

- 对内层包重新进行一次路由查找

##### **step5**：nodeC第二次路由决策（回到第一层）

nodeC查

```
10.244.3.10 dev cali99999 scope link
```

丢进对应pod的veth

> cali99999 是一个虚拟网络接口



#### podA --> podB（跨node）完整流程 BGP

假设

```
Node A                         Node B
192.168.10.5                   192.168.10.6
Pod CIDR: 10.244.1.0/24        Pod CIDR: 10.244.2.0/24

PodA: 10.244.1.5               PodB: 10.244.2.10
```

##### step0：calico提前做了什么

宣告自己负责的pod网络（BGP）

```
Node A 宣告：10.244.1.0/24
Node B 宣告：10.244.2.0/24
```

学到对方的pod网络，写进本地路由

nodeA

```
10.244.2.0/24 via 192.168.10.6 dev eth0
```

nodeB

```
10.244.1.0/24 via 192.168.10.5 dev eth0
```

##### step1：podA发包

```
src = 10.244.1.5
dst = 10.244.2.10
```

podA路由表

```
default via 169.254.1.1 dev eth0
```

包从 podA eth0 → veth → nodeA 的 caliA

##### step2：nodeA第一次路由查找（关键）





#### podA --> podB（同node）完整流程

假设

```
Node A

PodA: 10.244.1.5 --> PodB: 10.244.1.6

veth:
PodA eth0 <-> caliA
PodB eth0 <-> caliB
```

##### **step1**：podA发包

```
src = 10.244.1.5
dst = 10.244.1.6
```

podA路由表

```
default via 169.254.1.1 dev eth0
```

10.244.1.6 ≠ 我自己，走default，包从podA eth0出去

##### **step2**：进入node（第一次，也是唯一一次）

包通过veth到达node namepace的caliA，node开始接管，node查主路由表（由calico在pod创建时写进去）

```
10.244.1.6 dev caliB scope link
```

发现目标pod在我本机，且就在caliB这根线后面

##### **step3**：linux内核直接转发 ip_forward

因为net.ipv4.ip_forward = 1，所以内核允许caliA → caliB

##### **step4**：进入podB

包通过veth

```
caliB → PodB eth0
```





## Component architecture

![calico-components](https://docs.tigera.io/assets/images/architecture-calico-deae813300e472483f84d6bfb49650ab.svg)

### Calico API server

可以直接用kubectl来管理Calico资源



### Felix

calico的“大脑”，每个节点运行

k8s网络意图 --> linux内核的翻译和守护

写得是pod, service, networkPolicy的高级声明，Felix变成低级指令 veth, route, iptables

> main task：在主机上编辑路由、ACL、接口等，确保端点（pod/vm）能按策略通信

#### Interface management

- 配置内核接口，使内核可以正确处理pod流量

  > calico在pod创建的时候，向linux内核注册网络信息

  - 创建veth pair（一端进pod，一端留在主机叫caliXXX）
  - 给pod的eth0配IP
  - 在主机上添加直连路由 `10.244.1.2 dev cali12345 scope link`

- 主机在收到每个工作负载的 ARP 请求时，用自己的 MAC 地址回应

  pod会发 ARP 问 “谁是 169.254.1.1？”（虚拟 IP）

  虽然主机的caliXXXX接口没有配这个IP

  但calico开启了proxy_arp=1，让主机代答ARP，返回宿主机的MAC（即caliXXX的MAC），这样pod才愿意把包发过来

  对于pod来说，就是“下一跳设备“的MAC

- 启用 IP 转发

  calico确保系统开启了net.ipv4.ip_forward=1，主机才会当中间人，把从cali12345收到的包，转发给cali67890（同节点）或eth0/tunl0（跨节点）

- 持续监控

  如果有人手动删除了路由，或者pod重启，calico的agent（如calico-node）会持续watch接口和状态

  一旦发现配置丢失，就重新写入正确的路由、ARP、iptables的规则

> ✅ 这就是“声明式网络”的体现：始终趋近于期望状态



#### Route programming

查 FIB → 注入 caliXXX

calico会把本机每个pod的IP路由条目写入linux的内核转发表（FIB），例如”直连路由“

```
10.244.1.2 dev cali12345 scope link
10.244.1.5 dev cali56789 scope link
```

> FIB（Forwarding Information Base）是是内核中实际用于转发决策的数据结构

写了这些路由，当目标为本地pod的包到达主机时，内核才知道该把它“转交”给对应的 veth 接口，最终送达pod



#### ACL programming

ACL是Access Control List 访问控制列表

linux内核中，calico实际是通过iptables来实现ACL的，每条NetworkPolicy最终都会被Felix转换成一组iptables规则

比如写了

```
allow:
  from:
    namespace: frontend
  to:
    podSelector: {app: db}
```

Felix 会生成 iptables 规则，只允许来自 frontend 命名空间的pod访问 db pod；其他流量，比如backend ns的pod --> db被DROP

> 即使pod有root权限也无法绕过这些规则
>
> 因为规则实在主机内核网络栈的入口/出口处强制执行的
>
> 出向egress：包从caliXXX接口生成时，先过iptables的OUTPUT
>
> 入向ingress：包进入caliXXX前，先过iptables INPUT



#### State reporting

健康检测的探针，持续检查veth是否创建成功，路由是否写入FIB，iptables规则是否生效，BGP邻居是否连通，IP池是否足够

如果碰到报错，Felix会主动上报到datastore（通常是api server），写入NodeStatus或WorkloadEndpoint的状态对象

让集群知道这台机器的网络配置到底有没有成功

如果一台pod无法通信，发现某个endpoint的状态是Error，问题就是出在Felix配置阶段，而非应用本身



💡 **Policy-only mode**：

若设置 `CALICO_NETWORKING_BACKEND=none`，则 Felix **不启动 BIRD/confd**，仅做策略（适用于云托管集群如 EKS/GKE，网络由云平台提供）



#### BIRD

BIRD Internet Routing Daemon，是一个开源的、成熟的 互联网级路由软件，calico用它来实现 节点间的 BGP 路由同步

**BGP是协议，BIRD是一个BGP实现**

> 运行在每个运行了Felix的节点上，即每个k8s的work node

>  main task：从 Felix 获取路由，并通过 BGP 广播给其他节点

Felix负责管理本机pod的路由，BIRD的任务是把这些pod CIDR路由广播给集群内的其他节点

> pod CIDR = Kubernetes 给“某一台 Node”划的一整段 Pod IP 地址池
>
> 这台node以后创建的pod，只能从这段IP里拿

#### **Route distribution**

```
Calico
  |
  |-- Felix   → 写 /32 路由 + 策略
  |
  |-- BIRD    → 跑 BGP 协议，写 /24 路由
               ↑
               |（使用 BGP 这个协议）
```

Felix 写的是 /32 路由（每个 Pod）用于本机转发（同节点通信），BIRD 广播的是 /24用于跨节点路由

> /32指前32位是网络号，全是网络位，10.244.1.5/32只匹配一个IP，目标就是10.244.1.5
>
> /24指前24位是网络号，10.244.1.0/24指10.244.1.0  ~ 10.244.1.255

Calico 为每个 Node 分配一个 **唯一的 Pod CIDR**，比如：

- Node A → `10.244.1.0/24`
- Node B → `10.244.2.0/24`
- Node C → `10.244.3.0/24`

BIRD 通过 BGP 协议，向其他节点宣告

```
I own 10.244.1.0/24, next-hop = 192.168.10.5 (my Node IP)
```

Node B 收到后，写入自己的 FIB

```
ip route
# ...
10.244.1.0/24 via 192.168.10.5 dev eth0
```

---

如果BGP用/32会炸物理网络，路由表太大、路由更新太频繁、控制面震荡



#### **BGP route reflector configuration**

BGP Full Mesh全互联，连接数是n(n-1)/2，太多了

**解决方案：Route Reflector（RR）**

选几个节点作为Route Reflector（RR）

所有的普通节点（BIRD Client）只和RR连接

RR负责中转路由信息

- nodeA告诉RR：”我这里有10.244.1.0/24“
- RR告诉nodeB和nodeC：”nodeA有10.244.1.0/24“

📌 关键：RR 只参与控制平面（control plane），不转发数据包！数据包还是 Node A ↔ Node B 直接走物理网络

高可用：可以部署多个RR，普通节点同时连两个RR，一个挂了，另一个还能继续工作

```
        +------------------+
        |  Route Reflector |
        |  (Node RR1)      |
        +--------+---------+
                 ^
                 | BGP
    +------------+------------+
    |            |            |
+---v--+     +---v--+     +---v--+
|Node A|     |Node B|     |Node C|
|BIRD  |     |BIRD  |     |BIRD  |
+------+     +------+     +------+

Data Plane (actual pod traffic):
Node A <------------------> Node B   (direct, no RR involved!)
```



### confd

一个轻量级、开源的配置管理工具

> Main task：监听datastore（如api server或etcd）中的BGP配置变化，为BIRD更新配置文件.cfg，配置文件一变，就通知BIRD重载

| 配置项                  | 说明                                           | 为什么重要                               |
| ----------------------- | ---------------------------------------------- | ---------------------------------------- |
| BGP 配置                | 比如是否启用 BGP、对等体（peer）列表           | 决定节点要不要和其他节点建 BGP 连接      |
| AS number（自治系统号） | BGP 路由的“身份证”，默认 `64512`               | 同一集群必须一致，否则 BGP 邻居无法建立  |
| Logging levels          | BIRD 日志详细程度                              | 用于排错                                 |
| IPAM 信息               | 比如本节点分配到的 Pod CIDR（`10.244.1.0/24`） | Felix 和 BIRD 都需要知道“我负责哪个网段” |

BIRD本身不支持直接读api server或etcd，只认静态文件.cfg

所以confd就是这个桥梁，让BIRD保持无状态、只读配置文件（解耦）

📌 confd + BIRD 通常一起运行，除非在 policy-only 模式



#### **Dikastes**（高级功能，lstio集成）

> main task：在 Istio sidecar 中执行 **L7 网络策略**（如 HTTP 路径、方法）

【lsito】

前提：集群弃用了lstio服务网络

场景：pod已经注入了lstio的envoy sidecar

角色：作为Envoy的策略写作者，执行calico定义的L7网络策略

> 不是代替Envoy，而是增强Envoy的策略能力

做细粒度 API 级控制（如 `GET /api/v1/users` 允许，`DELETE /api/v1/users` 拒绝



#### CNI Plugin

pod网络初始化的入口点，calico和k8s首次握手的地方，也是pod网络诞生的起点

CNI是一套标准规范，定义了如何为pod配置网络，calico CNI Plugin就是calico实现这个规范的二进制程序（通常叫calico或calico-ipam）

当k8s要创建一个pod时，kubelet会调用CNI Plugin

只有在pod创建/删除的时候会被调用一次，之后就退出，不是daemon

每个节点都需要安装，通常放在/opt/cni/bin/calico

- `type: "calico"` → 告诉 kubelet 调用 `/opt/cni/bin/calico`
- `ipam: { "type": "calico-ipam" }` → 调用 `/opt/cni/bin/calico-ipam` 分配 IP

> 🔸 **Calico CNI = calico + calico-ipam 两个二进制文件协同工作**

依赖 Calico datastore（获取 IP 池），CNI Plugin 执行后，Felix 才能发现新 Pod 并管理它

💡 CNI Plugin 和 Felix 都读写同一个 datastore，但彼此不直接通信

##### pod创建全过程

kubelet调用CNI Plugin

CNI Plugin

- 从datastore获取可用IP（如10.244.1.5）
- 在主机创建cali12345
- 在pod namspace创建eth0，配IP+路由
- 退出

Felix（一直在运行）【通过datastore间接协作，没有直接调用】

- 监听到datastore中出现新的WorkloadEndpoint（Felix维护）
- 向内核添加路由10.244.1.5 dev cali12345 scope link
- 写iptables规则

BIRD/confd

- 如果本机CIDR是10.244.1.0/24，BIRD已经广播这个网段（无需等单个pod）
- 新Pod属于已有CIDR，不需要BIRD更新



### kube-controllers

#### IP Pool是谁维护的

calico-kube-controller

更准确地说：由 Calico 的控制器组件（Controller）负责 IP Pool 的生命周期管理，特别是 IPAM（IP Address Management）逻辑

##### 什么是IP Pool

是一个 CRD（Custom Resource Definition）

```
apiVersion: crd.projectcalico.org/v1
kind: IPPool
metadata:
  name: default-ipv4-ippool
spec:
  cidr: 10.244.0.0/16
  ipipMode: CrossSubnet
```

##### 谁创建/更新 IP Pool

初始配置由人创建，运行时的分配逻辑由控制器维护

```
calicoctl create -f ippool.yaml
# 或
kubectl apply -f ippool.yaml
```

##### 谁负责从IP Pool中分配具体IP

calico-kube-controllers 是一个独立的Deployment

包含多个控制器，其中**`ipam-controller`** 负责：

- 为每个 Node 分配 **Pod CIDR 块**（如 `10.244.1.0/24`）
- 回收不再使用的 IP 块
- 防止 IP 冲突

> 💡 注意：CNI Plugin（calico-ipam）在 Pod 创建时向 datastore 请求 IP，但 IP 的全局分配策略由 calico-kube-controllers 控制

##### 数据存储在哪里

k8s api中，作为CRD

```
kubectl get ippools.crd.projectcalico.org
```



#### WorkloadEndpoint是谁维护的

Felix是WEP对象的唯一写入者和维护者

##### 什么是WorkloadEndpoint

是 Calico 中表示 一个 Pod 网络端点 的 CRD

```
apiVersion: crd.projectcalico.org/v1
kind: WorkloadEndpoint
metadata:
  name: node1-k8s-mypod-eth0
  labels:
    app: myapp
spec:
  pod: mypod
  endpoint: eth0
  ipNetworks: ["10.244.1.5/32"]
  interfaceName: cali12345
```

包含pod name、IP、所在node、veth名、label...

##### 谁创建它

Felix

当CNI Plugin完成pod网络初始化后，Felix监听到k8s pod对象创建，会根据本地信息构造WEP对象并写入datastore

##### 为什么需要WEP

网络策略匹配依据：NetworkPlicy通过label selector匹配WEP

状态上报：运维人员可用通过`kubectl get workloadendpoinds`查看每个pod的网络状态

跨足剑共享信息：Typha、Dikastes

##### 谁读取WEP

Felix、Typha、Dikastes、运维





### **Typha**

Typha 是一个“共享缓存代理”，让 1000 个 Felix 节点只用 1 个连接访问 datastore，避免 API Server 被压垮

| 功能       | 说明                                                         |
| ---------- | ------------------------------------------------------------ |
| 单连接聚合 | Typha 只开 1 个 watch 连接到 datastore                       |
| 状态缓存   | 内存中缓存所有 Calico 对象（IPPool, WEP, Policy...）         |
| 事件去重   | 合并连续更新（如 Pod IP 快速变更）                           |
| 智能过滤   | 只把 相关更新 推送给每个 Felix （例如：Node A 只收本机 WEP + 全局策略） |
| 多路分发   | 通过 gRPC 或 HTTP/2 长连接推送给数百个 Felix                 |





### Plugins for cloud orchestrators

calico和k8s之间的翻译器

让用户觉得calico是k8s自带的组件，用起来很丝滑





### calicoctl

kubectl for Calico CRDs

```
# 查看节点 BGP 状态
calicoctl node status

# 应用策略
calicoctl apply -f policy.yaml

# 查看 WorkloadEndpoint
calicoctl get workloadendpoints -o wide

# 查看 IP Pool 使用情况
calicoctl ipam show
```



```
+---------------------+
|   User / Operator   |
|  (calicoctl / kubectl) 
+----------+----------+
           ↓
+----------+----------+
| Orchestrator Plugin |
| (e.g. calico-kube-controllers)
+----------+----------+
           ↓
+----------+----------+     +------------------+
|      Datastore      |<--->|      Typha       | ← (大规模集群必需)
| (K8s API / etcd)    |     +--------+---------+
+----------+----------+              |
           ↑                         ↓
+----------+----------+     +--------+---------+
|        CNI Plugin   |     |      Felix       | ← (每节点)
| (Pod 网络初始化)     |     +--------+---------+
+----------+----------+              |
           ↑                         ↓
+----------+----------+     +--------+---------+
|        Workloads    |     |       BIRD       | ← (BGP 路由)
|        (Pods)       |     +--------+---------+
+---------------------+              |
                                     ↓
                             +-------+--------+
                             |   Linux Kernel |
                             | (FIB, iptables)|
                             +----------------+
```

