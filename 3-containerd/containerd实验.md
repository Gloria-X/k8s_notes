## 环境准备

[containerd/docs/getting-started.md at main · containerd/containerd](https://github.com/containerd/containerd/blob/main/docs/getting-started.md)

确认系统使用cgroup v2

```
jcjy@jcjy-msi:~$ cat /sys/fs/cgroup/cgroup.controllers
cpuset cpu io memory hugetlb pids rdma misc
```

查看软件包是否已安装

```
jcjy@jcjy-msi:~$ dpkg -l | grep -E '^\ii\s+(curl|wget|git|docker\.io|containerd)'
ii  containerd.io                                 1.7.27-1                                amd64        An open and reliable container runtime
ii  curl                                          7.81.0-1ubuntu1.20                      amd64        command line tool for transferring data with URL syntax
ii  git                                           1:2.34.1-1ubuntu1.15                    amd64        fast, scalable, distributed revision control system
ii  git-man                                       1:2.34.1-1ubuntu1.15                    all          fast, scalable, distributed revision control system (manual pages)
ii  wget                                          1.21.2-2ubuntu1.1                       amd64        retrieves files from the web
```

检查containerd服务状态

```
jcjy@jcjy-msi:~$ systemctl is-active containerd
active
```

查看配置文件

```
jcjy@jcjy-msi:~$ cat /etc/containerd/config.toml
...
[plugins]
	...
	SystemdCgroup = true
```

启用此选项意味着容器的 Cgroup（资源控制）将由 Systemd 来管理，而不是 Containerd 自己管理。这是 Kubernetes 1.24+ 版本推荐的配置，对于实验环境的资源监控和清理非常重要



## 理解cgroup v2

隔离！！这是linux自身提供的能力

cgroup（control group）是一个层级结构，一个目录就是一个group，group下面还可以再建group，规则受上级group的限制

查看cgroup 目录 /sys/fs/cgroup

```
jcjy@jcjy-msi:/sys/fs/cgroup$ ls
cgroup.controllers      dev-hugepages.mount  memory.pressure
cgroup.max.depth        dev-mqueue.mount     memory.stat
cgroup.max.descendants  init.scope           misc.capacity
cgroup.procs            io.cost.model        proc-fs-nfsd.mount
cgroup.stat             io.cost.qos          proc-sys-fs-binfmt_misc.mount
cgroup.subtree_control  io.pressure          sys-fs-fuse-connections.mount
cgroup.threads          io.prio.class        sys-kernel-config.mount
cpu.pressure            io.stat              sys-kernel-debug.mount
cpuset.cpus.effective   kubepods.slice       sys-kernel-tracing.mount
cpuset.mems.effective   machine.slice        system.slice
cpu.stat                memory.numa_stat     user.slice
```

创建一个cgroup目录

```
cd /sys/fs/cgroup
sudo mkdir test-group
```

进入后会看到一些控制文件

```
jcjy@jcjy-msi:/sys/fs/cgroup$ cd test-group/
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ ll
total 0
drwxr-xr-x  2 root root 0 Feb  6 03:40 ./
dr-xr-xr-x 16 root root 0 Feb  6 03:40 ../
-r--r--r--  1 root root 0 Feb  6 03:40 cgroup.controllers  # 【只读】显示当前 cgroup 支持哪些控制器（如 cpu, memory, io, pids 等）
-r--r--r--  1 root root 0 Feb  6 03:40 cgroup.events  # 显示事件，如 populated 0 表示该 cgroup 是否还有进程
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.freeze  # 写入 1 冻结该 cgroup 中所有进程，写 0 解冻
--w-------  1 root root 0 Feb  6 03:40 cgroup.kill  ## 写入 1 会立即杀死该 cgroup 中所有进程（暴力清理）
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.max.depth
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.max.descendants
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.procs  # 写入进程PID，将该进程加入此 cgroup
-r--r--r--  1 root root 0 Feb  6 03:40 cgroup.stat
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.subtree_control  # 启用子控制器，例如写入 +memory +cpu 表示在此 cgroup 及其子 cgroup 中启用内存和 CPU 控制
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.threads  # 写入单个线程TID，较少用
-rw-r--r--  1 root root 0 Feb  6 03:40 cgroup.type
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.idle  # 设置低优先级（idle）任务权重（高级用法）
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.max  # 限制 CPU 带宽，格式：<quota> <period>（单位微秒）；例如 50000 100000 = 最多使用 50% 一个 CPU 核心；写 max 表示不限制
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.max.burst
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.pressure
-rw-r--r--  1 root root 0 Feb  6 03:40 cpuset.cpus
-r--r--r--  1 root root 0 Feb  6 03:40 cpuset.cpus.effective
-rw-r--r--  1 root root 0 Feb  6 03:40 cpuset.cpus.partition
-rw-r--r--  1 root root 0 Feb  6 03:40 cpuset.mems
-r--r--r--  1 root root 0 Feb  6 03:40 cpuset.mems.effective
-r--r--r--  1 root root 0 Feb  6 03:40 cpu.stat  # 【只读】显示 CPU 使用统计（如 usage、throttled 时间等）
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.uclamp.max  # 设置 CPU 利用率钳位（用于实时性保障）【TDOO: 中文也看不懂】
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.uclamp.min
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.weight
-rw-r--r--  1 root root 0 Feb  6 03:40 cpu.weight.nice
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.1GB.current
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.1GB.events
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.1GB.events.local
-rw-r--r--  1 root root 0 Feb  6 03:40 hugetlb.1GB.max  # 限制 1GB 大页内存使用量【TODO: 这个也不知道什么意思】
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.1GB.rsvd.current
-rw-r--r--  1 root root 0 Feb  6 03:40 hugetlb.1GB.rsvd.max
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.2MB.current
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.2MB.events
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.2MB.events.local
-rw-r--r--  1 root root 0 Feb  6 03:40 hugetlb.2MB.max  # 限制 2MB 大页内存使用量【TODO: 这个也不知道什么意思】
-r--r--r--  1 root root 0 Feb  6 03:40 hugetlb.2MB.rsvd.current
-rw-r--r--  1 root root 0 Feb  6 03:40 hugetlb.2MB.rsvd.max
-rw-r--r--  1 root root 0 Feb  6 03:40 io.max  # 限制磁盘 IO 带宽或 IOPS，格式复杂，例如：
8:0 rbps=1048576 wbps=max riops=max wiops=100
-rw-r--r--  1 root root 0 Feb  6 03:40 io.pressure
-rw-r--r--  1 root root 0 Feb  6 03:40 io.prio.class
-r--r--r--  1 root root 0 Feb  6 03:40 io.stat  # 【只读】显示各设备的 IO 使用情况
-rw-r--r--  1 root root 0 Feb  6 03:40 io.weight  # IO 调度权重（类似 cpu.weight）
-r--r--r--  1 root root 0 Feb  6 03:40 memory.current  # 【只读】当前实际使用的内存（含缓存）
-r--r--r--  1 root root 0 Feb  6 03:40 memory.events
-r--r--r--  1 root root 0 Feb  6 03:40 memory.events.local
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.high  # 软限制，超过后会施加压力（回收内存），但不一定会 kill
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.low  # 保护性内存，防止被全局回收（min > low）
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.max  # 硬限制内存使用量（字节），超过会触发 OOM kill
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.min  # 保护性内存，防止被全局回收（min > low）
-r--r--r--  1 root root 0 Feb  6 03:40 memory.numa_stat
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.oom.group
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.pressure  # PSI（Pressure Stall Information）指标，反映内存压力
-r--r--r--  1 root root 0 Feb  6 03:40 memory.stat  # 详细内存统计（anon, file, swap 等）
-r--r--r--  1 root root 0 Feb  6 03:40 memory.swap.current
-r--r--r--  1 root root 0 Feb  6 03:40 memory.swap.events
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.swap.high
-rw-r--r--  1 root root 0 Feb  6 03:40 memory.swap.max
-r--r--r--  1 root root 0 Feb  6 03:40 misc.current
-rw-r--r--  1 root root 0 Feb  6 03:40 misc.max
-r--r--r--  1 root root 0 Feb  6 03:40 pids.current  # 当前进程数
-r--r--r--  1 root root 0 Feb  6 03:40 pids.events
-rw-r--r--  1 root root 0 Feb  6 03:40 pids.max  # 限制该 cgroup 中最大进程/线程数量；设为 max 则无限制
-r--r--r--  1 root root 0 Feb  6 03:40 rdma.current
-rw-r--r--  1 root root 0 Feb  6 03:40 rdma.max
```

查看父级使用了那些控制器传递

```
jcjy@jcjy-msi:/sys/fs/cgroup$ cat cgroup.subtree_control
cpuset cpu io memory hugetlb pids rdma misc
```

查看test-group层级下是否允许使用这些控制器

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ cat cgroup.controllers
cpuset cpu io memory hugetlb pids rdma misc
```

* 如果需要test-group的子级也能使用这些控制器，则需要在test-group中的subtree_control里设置，如

  ```
  echo "+cpu +memory" | sudo tee test-group/cgroup.subtree_control
  ```

现在的情况下完全可用在test-group中使用这些控制器



### 实训：CPU限制

cpu.max的格式

```
cpu.max = <quota> <period>
```

- 100000 = 100ms
- 10000 100000 = 最多用 10% CPU

设置cpu限制

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ echo "10000 100000" | sudo tee cpu.max
10000 100000
```

写一个占cpu的例子

```
# cpu_burn_timed.py
import multiprocessing
import time
import sys
import os

def burn_cpu(duration=60):
    """占用 CPU 指定时间（秒）"""
    end_time = time.time() + duration
    x = 0
    pid = os.getpid()
    while time.time() < end_time:
        x += 1
        if x % 5000000 == 0:  # 增加间隔避免太多输出
            elapsed = time.time() - (end_time - duration)
            print(f"PID {pid}: {elapsed:.1f}/{duration}s, iterations: {x:,}")
    print(f"Process {pid} completed {x:,} iterations")
    return x

if __name__ == "__main__":
    # 允许通过参数控制进程数
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    num_processes = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"Running {num_processes} process(es) for {duration} seconds...")
    
    if num_processes == 1:
        # 单进程模式
        result = burn_cpu(duration)
        print(f"Single process completed with {result:,} iterations")
    else:
        # 多进程模式
        processes = []
        for _ in range(num_processes):
            p = multiprocessing.Process(target=burn_cpu, args=(duration,))
            p.start()
            processes.append(p)
        
        for p in processes:
            p.join()
        
        print("All processes completed.")

# 秒数 进程数
# python3 cpu_burn_timed.py 30 1

```

#### 单进程

在test-group中执行程序

```
sudo sh -c 'echo $$ > /sys/fs/cgroup/test-group/cgroup.procs && exec python3 /home/jcjy/xsy-project/containerd/cpu_burn_timed.py 60 1'
```

查看进程状态

```
jcjy@jcjy-msi:~$ cat /sys/fs/cgroup/test-group/cgroup.procs
514988
```

查看资源占用

```
jcjy@jcjy-msi:~$ top
top - 06:48:48 up 69 days, 23:49,  4 users,  load average: 2.26, 1.77, 1.59
Tasks: 689 total,   2 running, 687 sleeping,   0 stopped,   0 zombie
%Cpu(s): 12.5 us,  4.6 sy,  0.0 ni, 82.7 id,  0.1 wa,  0.0 hi,  0.1 si,  0.0 st
MiB Mem :  31945.6 total,   2664.6 free,  14957.5 used,  14323.5 buff/cache
MiB Swap:      0.0 total,      0.0 free,      0.0 used.  16409.7 avail Mem

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
4160219 syslog    20   0   10.2g   7.5g  12584 S  51.3  24.1  43934:45 qemu-kvm
 514988 root      20   0   17856  10616   6044 R  10.3   0.0   0:01.12 python3
...
```

查看cpu status

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ cat cpu.stat
usage_usec 28304090  # 当前 cgroup 实际使用的 CPU 时间:28.3s，是程序实际获得的CPU时间
user_usec 28199483
system_usec 104606
nr_periods 2840  # CPU 配额检查的周期数，每个周期默认是 100ms，表示监控了 284 秒的时间
nr_throttled 2823  # 关键！被限制（throttled）的周期数量，2823 / 2840 = 99.4% 的周期都被限制了，几乎每个 100ms 周期内，进程都提前用完了配额
throttled_usec 541885816  # 累计被限制的时间，进程想用但被拒绝的 CPU 时间:541.9s ≈ 9min
```

```
周期 1: [✓✓✓✓✓✓✓✓✓✓] 用了 10ms，配额用完 → 被限制(throttled)
周期 2: [✓✓✓✓✓✓✓✓✓✓] 用了 10ms，配额用完 → 被限制(throttled)
周期 3: [✓✓✓✓✓✓✓✓✓✓] 用了 10ms，配额用完 → 被限制(throttled)
...
周期 2823: [✓✓✓✓✓✓✓✓✓✓] 用了 10ms，配额用完 → 被限制(throttled)
周期 2824: [✓✓✓✓✓✓] 只用了 6ms，还没用完配额 → 未被限制
...
```



##### 如果cpu.max放开了max 100000

```
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 555891 root      20   0   17856  10392   5820 R 100.0   0.0   0:25.69 python3
 ...
```

查看cpu status

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ cat cpu.stat
usage_usec 13179712
user_usec 13175712
system_usec 3999
nr_periods 0
nr_throttled 0
throttled_usec 0
```

> nr_periods, nr_throttled, throttled_usec都是0！！说明完全没有被限制

💡注意！！cpu.stat不能像memory.stat一样重置，要删组重建

```
$ sudo rmdir /sys/fs/cgroup/test-group

$ sudo mkdir /sys/fs/cgroup/test-group
```



#### 多进程

在test-group中执行程序

```
sudo sh -c 'echo $$ > /sys/fs/cgroup/test-group/cgroup.procs && exec python3 /home/jcjy/xsy-project/containerd/cpu_burn_timed.py 30 8'
```

查看进程状态

```
jcjy@jcjy-msi:~$ cat /sys/fs/cgroup/test-group/cgroup.procs
522658
522677
522678
```

522658：主进程

522677, 522678：子进程（Python multiprocessing 创建的）

CPU时间分配：总配额10%（10ms/100ms），3个进程共享这10%的CPU

```
jcjy@jcjy-msi:~$ top
top - 06:51:10 up 69 days, 23:51,  4 users,  load average: 1.10, 1.50, 1.52
Tasks: 692 total,   3 running, 689 sleeping,   0 stopped,   0 zombie
%Cpu(s): 12.5 us,  5.1 sy,  0.0 ni, 82.0 id,  0.1 wa,  0.0 hi,  0.3 si,  0.0 st
MiB Mem :  31945.6 total,   2642.2 free,  14978.7 used,  14324.8 buff/cache
MiB Swap:      0.0 total,      0.0 free,      0.0 used.  16388.6 avail Mem

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
4160219 syslog    20   0   10.2g   7.5g  12584 S  53.5  24.1  43936:02 qemu-kvm
2704288 syslog    20   0 6902028   1.9g  22504 S  12.5   6.2   1193:47 qemu-kvm
   4105 root      20   0 4354420 155880  41408 S  11.6   0.5   8758:45 kubelet
1608485 root      20   0 2370716 992.9m  65260 S  11.2   3.1   2760:52 kube-apiserver
 522677 root      20   0   19016   7908   2948 R   5.0   0.0   0:01.09 python3
 522678 root      20   0   19016   7908   2948 R   5.0   0.0   0:01.06 python3
...

 514547 jcjy      20   0   11544   4984   3664 R   0.7   0.0   0:01.24 top
```



### 实训：内存限制+OOM

设置内存上限（50MB）

```
echo $((50 * 1024 * 1024)) | sudo tee memory.max
```

写一个消耗内存的程序

```
import sys
import time
import os

def real_memory_allocator():
    """真正分配并持有内存"""
    step_mb = 10
    step_bytes = step_mb * 1024 * 1024
    total_mb = 0
    allocated_chunks = []
    
    print(f"PID: {os.getpid()}")
    print("Starting real memory allocation...")
    
    try:
        while True:
            try:
                # 使用 bytearray 真正分配内存
                chunk = bytearray(step_bytes)
                # 写入数据确保分配
                chunk[0] = 1
                chunk[-1] = 255
                
                allocated_chunks.append(chunk)
                total_mb += step_mb
                
                print(f"✅ Allocated: {total_mb:4d} MB | Total: {len(allocated_chunks)} chunks")
                
                # 每 100MB 输出一次详细信息
                if total_mb % 100 == 0:
                    sys.stderr.write(f"Checkpoint: {total_mb} MB allocated\n")
                
            except MemoryError:
                print(f"❌ MemoryError at {total_mb} MB!")
                print("Waiting 30 seconds to observe OOM behavior...")
                
                # 保持内存不释放，观察 OOM killer
                for i in range(30, 0, -1):
                    print(f"Waiting {i} seconds...")
                    time.sleep(1)
                
                # 释放内存后继续尝试
                allocated_chunks.clear()
                print("Freed memory, will retry...")
                total_mb = 0
                time.sleep(2)
                continue
                
            time.sleep(0.2)  # 快速分配
            
    except KeyboardInterrupt:
        print(f"\nInterrupted. Final: {total_mb} MB")
        allocated_chunks.clear()
    
    return total_mb

if __name__ == "__main__":
    print("=== Memory Allocator ===")
    result = real_memory_allocator()
    print(f"Maximum allocated: {result} MB")

```

运行程序

```
sudo sh -c 'echo $$ > /sys/fs/cgroup/test-group/cgroup.procs && exec python3 /home/jcjy/xsy-project/containerd/memory_allocator.py'
```

监控关键指标

```
cat /sys/fs/cgroup/test-group/memory.events
cat /sys/fs/cgroup/test-group/memory.current
```

---

运行结果为

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ sudo sh -c 'echo $$ > /sys/fs/cgroup/test-group/cgroup.procs && exec python3 /home/jcjy/xsy-project/containerd/memory_allocator.py'
=== Memory Allocator ===
PID: 696386
Starting real memory allocation...
✅ Allocated:   10 MB | Total: 1 chunks
✅ Allocated:   20 MB | Total: 2 chunks
✅ Allocated:   30 MB | Total: 3 chunks
✅ Allocated:   40 MB | Total: 4 chunks
Killed
```

#### 验证 OOM Killer

查看系统日志

```
jcjy@jcjy-msi:~$ sudo dmesg | tail -20
                 workingset_activate_file 0
                 workingset_restore_anon 0
                 workingset_restore_file 0
                 workingset_nodereclaim 0
                 pgfault 14220
                 pgmajfault 0
                 pgrefill 0
                 pgscan 0
                 pgsteal 0
                 pgactivate 0
                 pgdeactivate 0
                 pglazyfree 0
                 pglazyfreed 0
                 thp_fault_alloc 0
                 thp_collapse_alloc 0
[6050275.006522] Tasks state (memory values in pages):
[6050275.006524] [  pid  ]   uid  tgid total_vm      rss pgtables_bytes swapents oom_score_adj name
[6050275.006527] [ 696386]     0 696386    17140    14270   176128        0             0 python3
[6050275.006538] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=test-group,mems_allowed=0,oom_memcg=/test-group,task_memcg=/test-group,task=python3,pid=696386,uid=0
[6050275.006563] Memory cgroup out of memory: Killed process 696386 (python3) total-vm:68560kB, anon-rss:50852kB, file-rss:6228kB, shmem-rss:0kB, UID:0 pgtables:172kB oom_score_adj:0
```

查看cgroup的OOM计数

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ cat memory.events
low 0
high 0
max 35
oom 1  # OOM 事件发生次数
oom_kill 1  # OOM 杀死进程次数
```

查看memory.current

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ cat /sys/fs/cgroup/test-group/memory.current
4096
```

内存限制设置为50MB，加上python自身的内存开销，程序在分配到40MB的时候 OOM

重置memory.current直接 vim 改成0即可



### 进程数量限制（pids）

设置pids.max

```
echo 10 | sudo tee pids.max
```

写一个进程炸弹

```
import os
import sys
import time

def simple_fork_test(max_forks=100):
    """简单的 fork 测试，用于 pids cgroup 测试"""
    print(f"测试进程限制")
    print(f"主进程 PID: {os.getpid()}")
    print("")
    
    children = []
    try:
        for i in range(1, max_forks + 1):
            try:
                pid = os.fork()
                if pid == 0:
                    # 子进程：休眠然后退出
                    time.sleep(60)  # 休眠60秒
                    os._exit(0)
                else:
                    # 父进程：记录子进程
                    children.append(pid)
                    print(f"创建子进程 #{i}: PID {pid}")
                    time.sleep(0.01)  # 短暂延迟
                    
            except OSError as e:
                print(f"❌ 创建第 {i} 个进程时失败: {e}")
                print(f"总共成功创建了 {len(children)} 个进程")
                break
        
        # 等待
        print(f"\n总共创建了 {len(children)} 个子进程")
        print("等待30秒观察...")
        time.sleep(30)
        
        # 清理
        print("清理子进程...")
        for pid in children:
            try:
                os.kill(pid, 9)
            except:
                pass
        
    except KeyboardInterrupt:
        print("\n用户中断，清理进程...")
        for pid in children:
            try:
                os.kill(pid, 9)
            except:
                pass
    
    print("测试完成")

if __name__ == "__main__":
    simple_fork_test(200)  # 尝试创建200个进程

```

运行程序

```
sudo sh -c 'echo $$ > /sys/fs/cgroup/test-group/cgroup.procs && exec python3 /home/jcjy/xsy-project/containerd/pids_fork.py'
```

运行过程

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ sudo sh -c 'echo $$ > /sys/fs/cgroup/test-group/cgroup.procs && exec python3 /home/jcjy/xsy-project/containerd/pids_fork.py'
测试进程限制
主进程 PID: 754740

创建子进程 #1: PID 754741
创建子进程 #2: PID 754742
创建子进程 #3: PID 754743
创建子进程 #4: PID 754744
创建子进程 #5: PID 754745
创建子进程 #6: PID 754746
创建子进程 #7: PID 754747
创建子进程 #8: PID 754748
创建子进程 #9: PID 754749
❌ 创建第 10 个进程时失败: [Errno 11] Resource temporarily unavailable
总共成功创建了 9 个进程

总共创建了 9 个子进程
等待30秒观察...
清理子进程...
测试完成
```

查看pid.current

```
jcjy@jcjy-msi:/sys/fs/cgroup/test-group$ cat pids.current
10
```

符合预期



## 查找pod对应的cgroup

### pod内的cgroup

pod是一个cgroup目录，container是pod下面的子cgroup

QoS是pod所在的父目录

pod中看不到完整的cgroup树，但能看到自己被限制了什么

> k8s没有给cgroup namespace，但会把相关文件bind mount进来

查看pod中可看到的cgroup信息

```
jcjy@jcjy-msi:~$ kubectl exec -it middleware-mysql-0 -n ai-deliver -- /bin/sh
$ ls
cgroup.controllers      cgroup.type      cpuset.cpus               hugetlb.1GB.rsvd.max      io.stat              memory.oom.group     pids.events
cgroup.events           cpu.idle         cpuset.cpus.effective     hugetlb.2MB.current       io.weight            memory.pressure      pids.max
cgroup.freeze           cpu.max          cpuset.cpus.partition     hugetlb.2MB.events        memory.current       memory.stat          rdma.current
cgroup.kill             cpu.max.burst    cpuset.mems               hugetlb.2MB.events.local  memory.events        memory.swap.current  rdma.max
cgroup.max.depth        cpu.pressure     cpuset.mems.effective     hugetlb.2MB.max           memory.events.local  memory.swap.events
cgroup.max.descendants  cpu.stat         hugetlb.1GB.current       hugetlb.2MB.rsvd.current  memory.high          memory.swap.high
cgroup.procs            cpu.uclamp.max   hugetlb.1GB.events        hugetlb.2MB.rsvd.max      memory.low           memory.swap.max
cgroup.stat             cpu.uclamp.min   hugetlb.1GB.events.local  io.max                    memory.max           misc.current
cgroup.subtree_control  cpu.weight       hugetlb.1GB.max           io.pressure               memory.min           misc.max
cgroup.threads          cpu.weight.nice  hugetlb.1GB.rsvd.current  io.prio.class             memory.numa_stat     pids.current
$ cat /sys/fs/cgroup/cpu.max
max 100000
$ cat /sys/fs/cgroup/memory.max
max
$ cat /sys/fs/cgroup/pids.max
38095

```



### 宿主机上找对应的cgroup

查看pod UID

```
jcjy@jcjy-msi:~$ kubectl get pod virt-launcher-centos7-v8srl -n ai-deliver -o jsonpath='{.metadata.uid}'
f3d89456-0ba1-4ff6-b4db-cea66e77e923
```

直接通过容器信息查找

```
jcjy@jcjy-msi:~$ CONTAINER_ID=$(sudo crictl ps -o json | jq -r '
  .containers[] |
  select(.labels["io.kubernetes.pod.uid"] == "f3d89456-0ba1-4ff6-b4db-cea66e77e923") |
  .id'
)

echo "容器ID: $CONTAINER_ID"

# 然后通过容器ID查看cgroup信息
if [ -n "$CONTAINER_ID" ]; then
    # 查看容器的cgroup路径
    sudo crictl inspect $CONTAINER_ID | jq -r '.info.runtimeSpec.linux.cgroupsPath'

    # 或者查看完整的运行时信息
    sudo crictl inspect $CONTAINER_ID | jq '.info.runtimeSpec.linux'
fi
容器ID: fb7d2dcede9bfdbdd222c647f285cb3d21659b60eb72228e209e54570864e167
358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93
kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice:cri-containerd:fb7d2dcede9bfdbdd222c647f285cb3d21659b60eb72228e209e54570864e167
kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice:cri-containerd:358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93
{
  "resources": {
    "devices": [
      {
        "allow": false,
        "access": "rwm"
      }
    ],
    "memory": {
      "limit": 60000000,
      "swap": 60000000
    },
    "cpu": {
      "shares": 5,
      "quota": 1500,
      "period": 100000
    },
    "unified": {
      "memory.oom.group": "1",
      "memory.swap.max": "0"
    }
  },
  "cgroupsPath": "kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice:cri-containerd:fb7d2dcede9bfdbdd222c647f285cb3d21659b60eb72228e209e54570864e167",
  "namespaces": [
    {
      "type": "pid"
    },
    {
      "type": "ipc",
      "path": "/proc/2703925/ns/ipc"
    },
    {
      "type": "uts",
      "path": "/proc/2703925/ns/uts"
    },
    {
      "type": "mount"
    },
    {
      "type": "network",
      "path": "/proc/2703925/ns/net"
    },
    {
      "type": "cgroup"
    }
  ],
  "maskedPaths": [
    "/proc/asound",
    "/proc/acpi",
    "/proc/kcore",
    "/proc/keys",
    "/proc/latency_stats",
    "/proc/timer_list",
    "/proc/timer_stats",
    "/proc/sched_debug",
    "/proc/scsi",
    "/sys/firmware",
    "/sys/devices/virtual/powercap"
  ],
  "readonlyPaths": [
    "/proc/bus",
    "/proc/fs",
    "/proc/irq",
    "/proc/sys",
    "/proc/sysrq-trigger"
  ]
}
{
  "resources": {
    "devices": [
      {
        "allow": false,
        "access": "rwm"
      },
      {
        "allow": true,
        "type": "c",
        "major": 10,
        "minor": 200,
        "access": "rwm"
      },
      {
        "allow": true,
        "type": "c",
        "major": 10,
        "minor": 238,
        "access": "rwm"
      },
      {
        "allow": true,
        "type": "c",
        "major": 10,
        "minor": 232,
        "access": "rwm"
      }
    ],
    "memory": {},
    "cpu": {
      "shares": 102,
      "period": 100000
    },
    "unified": {
      "memory.oom.group": "1",
      "memory.swap.max": "0"
    }
  },
  "cgroupsPath": "kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice:cri-containerd:358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93",
  "namespaces": [
    {
      "type": "pid"
    },
    {
      "type": "ipc",
      "path": "/proc/2703925/ns/ipc"
    },
    {
      "type": "uts",
      "path": "/proc/2703925/ns/uts"
    },
    {
      "type": "mount"
    },
    {
      "type": "network",
      "path": "/proc/2703925/ns/net"
    },
    {
      "type": "cgroup"
    }
  ],
  "devices": [
    {
      "path": "/dev/net/tun",
      "type": "c",
      "major": 10,
      "minor": 200,
      "fileMode": 438,
      "uid": 0,
      "gid": 0
    },
    {
      "path": "/dev/vhost-net",
      "type": "c",
      "major": 10,
      "minor": 238,
      "fileMode": 432,
      "uid": 0,
      "gid": 108
    },
    {
      "path": "/dev/kvm",
      "type": "c",
      "major": 10,
      "minor": 232,
      "fileMode": 432,
      "uid": 0,
      "gid": 108
    }
  ],
  "rootfsPropagation": "rslave",
  "maskedPaths": [
    "/proc/asound",
    "/proc/acpi",
    "/proc/kcore",
    "/proc/keys",
    "/proc/latency_stats",
    "/proc/timer_list",
    "/proc/timer_stats",
    "/proc/sched_debug",
    "/proc/scsi",
    "/sys/firmware",
    "/sys/devices/virtual/powercap"
  ],
  "readonlyPaths": [
    "/proc/bus",
    "/proc/fs",
    "/proc/irq",
    "/proc/sys",
    "/proc/sysrq-trigger"
  ]
}
```

这个pod有两个容器：

- 第一个容器ID：fb7d2dcede9bfdbdd222c647f285cb3d21659b60eb72228e209e54570864e167
- 第二个容器ID：358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93

两个容器共享相同的cgroup路径前缀：kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice



查看实际的cgroup目录

```
ls -la /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice/
```

执行结果：

```
jcjy@jcjy-msi:~$ ls -la /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice/
total 0
...
drwxr-xr-x  2 root root 0 Jan 26 08:31 cri-containerd-358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93.scope
drwxr-xr-x  2 root root 0 Jan 26 08:31 cri-containerd-9a9dc90e4188aeddf1c2f54b24b51a5222119f5965fcc1e8cacc064684b708ad.scope
drwxr-xr-x  2 root root 0 Jan 26 08:31 cri-containerd-fb7d2dcede9bfdbdd222c647f285cb3d21659b60eb72228e209e54570864e167.scope
...
```

看起来好像有三个container

但 9a9dc90e4188aeddf1c2f54b24b51a5222119f5965fcc1e8cacc064684b708ad 已退出，猜测可能是init container

查看 procs

```
jcjy@jcjy-msi:~$ cat /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice/cri-containerd-358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93.scope/cgroup.procs
2703979
2704077
2704114
2704116
2704288
3090146
jcjy@jcjy-msi:~$ cat /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice/cri-containerd-9a9dc90e4188aeddf1c2f54b24b51a5222119f5965fcc1e8cacc064684b708ad.scope/cgroup.procs
2703925
jcjy@jcjy-msi:~$ cat /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podf3d89456_0ba1_4ff6_b4db_cea66e77e923.slice/cri-containerd-fb7d2dcede9bfdbdd222c647f285cb3d21659b60eb72228e209e54570864e167.scope/cgroup.procs
2704090
```

358e66cc1ed6dfea43837c0ee70eeb306fcafdb0cec5657cf76e9ba3bbef8c93 是compute容器，另一个是guest-console-log

可确认：

```
jcjy@jcjy-msi:~$ kubectl get pod virt-launcher-centos7-v8srl -n ai-deliver -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}'
compute
guest-console-log
```















