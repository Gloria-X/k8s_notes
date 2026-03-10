周一：
1. 用guacmole消费你自己的qemu开出来vnc的端口，然后跑通。

1s数据量：1920 * 1080 * 3 * 1byte * 60

qemu TCP 5901 （VGA ） <-- guac 消费  --> websocket （极大的压缩）  这个活是gucad干的

guacmole 只是一个web前端项目（不装也没事）


2. 用websocket客户端去连一下api server，然后看一下websocket里有什么东西


kubevirt把qemu的vnc 5901转发给了api server(k8s)

api server (websocket)  ---> pod --> qemu (vnc tcp)


3. 需要把websocket再转回到tcp，然后让guac消费 vnc-proxy 项目（跑起来，跑通）
https://gitlab.tiusolution.com/jcjy/vnc-proxy

guac(tcp client) -> (tcp server)vnc-proxy(websocket client) -> api-server(websocket server)


```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: centos7
spec:
  running: true
  template:
    spec:
      domain:
        cpu:
          cores: 1
        devices:
          disks:
            - name: disk
              bootOrder: 1
              disk:
                bus: virtio
          interfaces:
            - name: default
              masquerade: {}
        machine:
          type: q35
        resources:
          requests:
            memory: 1G
      networks:
        - name: default
          pod: {}
      volumes:
        - name: disk
          persistentVolumeClaim:
            claimName: {pvc}
```



---



周二：
k8s的架构，给我讲一下，各种组件(控制面板,kubelet，kube-proxy)还有kind（deployment,service,pod,statefulset,replicaset,storage,ingress）

资源编排：
containerd
network
storage



---




周四：理解docker虚拟化(做实验) 主要是要理解cgroupv2

写一个最简单helm，然后 install 一下 helm(其实就是k8s的yaml的模板)

crictl containerd

| 内容                  | 所属层级                    | 与 containerd 的关系                                         |
| --------------------- | --------------------------- | ------------------------------------------------------------ |
| cgroup v2 实验        | Linux 内核资源控制层        | containerd（以及 runc）依赖 cgroup v2 来实现容器的资源限制（CPU、内存等） |
| Docker 虚拟化理解     | 容器抽象层（历史/对比视角） | Docker 默认使用 containerd 作为其后端运行时（自 Docker 18.09+），所以本质上也在用 containerd |
| crictl + containerd   | K8s 容器运行时接口（CRI）层 | crictl 是专为 CRI 设计的 CLI 工具，直接与 containerd（启用 CRI 插件时）通信 |
| Helm（K8s YAML 模板） | 编排管理层                  | Helm 部署的 Pod 最终由 K8s 调度到节点，由 containerd 启动容器 |

---

周五：关于network的实验(后续给任务)
主要是理解桥接网卡 iptable ufw防火墙 这三个

multus calico k8s网络插件


存储： cephfs cephrbd

​                                                        

---

cloud-init

fuse s3 乱试试

https://gitlab.tiusolution.com/jcjy-dev/sd-webui-docker/-/issues/124

跑通



---



image-xxx-cron 问老黄看逻辑



---

kubevirt和aliyun应该都有api看资源使用情况



---

我们的cpu配置和阿里云的cpu配置...



---

跨节点

P2P分发



---

pod快照

https://gitlab.tiusolution.com/jcjy-dev/sd-gateway/-/issues/19













