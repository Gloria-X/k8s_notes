



主要是理解桥接网卡 iptable ufw防火墙 这三个

multus calico k8s网络插件

存储： cephfs cephrbd





# 桥接网卡

[networking:bridge [Wiki\]](https://wiki.linuxfoundation.org/networking/bridge)

将多个网络接口“桥接”成一个逻辑接口，常用于虚拟化（如 KVM、Docker）中让 VM/容器共享宿主机网络



# iptables

[Iptables Tutorial 1.2.3](https://www.frozentux.net/iptables-tutorial/iptables-tutorial.html)

Linux 内核的包过滤/网络地址转换（NAT）框架，是理解网络策略、防火墙、K8s Service 实现的基础



# ufw

[Firewall - Ubuntu Server documentation](https://documentation.ubuntu.com/server/how-to/security/firewalls/)

iptables 的简化前端，适合快速配置主机防火墙





# calico

[About Calico | Calico Documentation](https://docs.tigera.io/calico/latest/about/?spm=5176.28103460.0.0.b2e87551DX3Jw1)







# multus

[k8snetworkplumbingwg/multus-cni: A CNI meta-plugin for multi-homed pods in Kubernetes](https://github.com/k8snetworkplumbingwg/multus-cni?spm=5176.28103460.0.0.b2e87551DX3Jw1)

[multus-cni/docs/how-to-use.md at master · k8snetworkplumbingwg/multus-cni](https://github.com/k8snetworkplumbingwg/multus-cni/blob/master/docs/how-to-use.md?spm=5176.28103460.0.0.b2e87551DX3Jw1&file=how-to-use.md)

支持“多网络接口”的 CNI 插件，允许 Pod 同时接入多个网络（如一个默认 Calico + 一个 SR-IOV 网络）



pod同时使用 Calico + macvlan





