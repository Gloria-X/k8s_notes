## iptables

Linux 内核里的“包处理规则表”

每个网络包进来/出去/转发的时候，内核就会按顺序问一些规则「你要不要处理这个包？」

实际有四表五链，但先玩以下

| Chain   | 含义                 |
| ------- | -------------------- |
| INPUT   | **进本机的包**       |
| OUTPUT  | **从本机出去的包**   |
| FORWARD | **经过本机转发的包** |

表：

- filter（默认）：放不放行（防火墙）
  - ACCEPT
  - DROP
  - REJECT
- nat（kube-proxy核心）：改地址、改端口
  - DNAT（改目标）
  - SNAT（改源）





我的实训机器中存在docker和k8s，不算裸机

查看当前规则

```bash
sudo iptables -L -n -v
```

先看INPUT链

```bash
Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
  21M 5404M KUBE-PROXY-FIREWALL  all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate NEW /* kubernetes load balancer firewall */
1987M  751G KUBE-NODEPORTS  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes health check service ports */
  21M 5404M KUBE-EXTERNAL-SERVICES  all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate NEW /* kubernetes externally-visible service portals */
1987M  751G KUBE-FIREWALL  all  --  *      *       0.0.0.0/0            0.0.0.0/0
1987M  751G LIBVIRT_INP  all  --  *      *       0.0.0.0/0            0.0.0.0/0
```

- `KUBE-*`：来自 Kubernetes 的网络规则。
- `LIBVIRT_*`：来自 libvirt（通常用于 QEMU/KVM 虚拟机）。
- 后面还有大量 `DOCKER-*` 规则，说明你装了 Docker 并运行了容器（比如 PostgreSQL、Redis、MinIO、RabbitMQ 等）。



换了台裸机

```
$ sudo iptables -L -n -v # 查看当前状态

Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
pkts bytes target prot opt in out source destination

Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
pkts bytes target prot opt in out source destination

Chain OUTPUT (policy ACCEPT 0 packets, 0 bytes)
pkts bytes target prot opt in out source destination
```



加规则，拒绝某个IP

```
sudo iptables -A INPUT -s 10.244.0.95 -j REJECT
```

```
root@ubuntu:～$ sudo iptables -A INPUT -s 10.244.0.95 -j REJECT
root@ubuntu:～$ sudo iptables -L -n -v
Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
pkts bytes target prot opt in out source destination
0     0 REJECT all -- * * 10.244.0.95 0.0.0.0/0
reject-with icmp-port-unreachable

Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
pkts bytes target prot opt in out source destination

Chain OUTPUT (policy ACCEPT 0 packets, 0 bytes)
pkts bytes target prot opt in out source destination
```







