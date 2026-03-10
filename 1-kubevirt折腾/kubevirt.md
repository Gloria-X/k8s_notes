用户指令

---

api server存对象(yaml的内容)

---

virt-controller
> 谁知道 api server 收到了一个开vm的请求
> 不是api server通知的，是controller watch到的

while true:
	watch API Server
		if xxxx:
			exec...

[watch + reconcile]

---

vm --> vmi 是 virt-controller 决定的

vm
↓
vmi(一个用来生成pod的kind) 【virt-controller 创建的】
↓
pod(跑virt-launcher) 【virt-controller创建的】

---k8s---

kube-scheduler 看到了没有 nodeName 的pod【virt-controller创建的】
根据各类资源 cpu, memory, label...
选一个 node
写回 yaml(pod.spec.nodeName = node3)


---node上还没有发生任何事情，只是做决定---

node3上的 kubelete

watch api-server
	if pod.spec.nodeName === node3

	拉镜像、创容器、挂载volume、配置网络ns、启动pod

> kubelet不知道什么是vm，只知道是个pod，具体的镜像、cmd都是virt-controller决定的


virt-launcher pod启动
Pod: virt-launcher-xxxx
Container: virt-launcher


virt-handler(DaemonSet，每个node一个)

watch vmi(api server上的吗)
	【kube-scheduler写pod的node，virt-controller watch某一个pod属于某个vmi且已经被调度，更新vmi.status.nodeName】
	if vmi.status.nodeName === node3:

	这个vmi归我管
	
	执行 VM 专属逻辑: 准备磁盘、创建bridge、...
	调用virt-launcher接口(通知一下可以起qemu了：libvirtd --> qemu-system-x86_64)
	
	qemu进程启动

vm对外可用