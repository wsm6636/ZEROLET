""" 
This file implements the proposed optimal task phasing for single chains.
- Optimal task phasing to minimize end-to-end latency for max-harmonic 
- Optimal task phasing to minimize end-to-end latency with (2,k)-max-harmonic periods
- Computation of end-to-end latency bound under both phasings

* optimalPhasingMaxHarm(chain)      -> max-harmonic periods
* optimalPhasing2kMaxHarm(chain)    -> (2,k)-max-harmonic periods
"""
from Time import *
from Task import *
import os
from DPT_Offset import *

def optimalPhasingMaxHarm(chain):
    """ Function assigns optimal task phases to minimize end-to-end latency 
        and returns the end-to-end latency bound. Theorem 10. 
    """
    
    # Set task phases to be optimal (Definition 9)
    offset = 0

    for task in chain:
        task.offset = offset
        offset = offset + task.period

    # Compute the latency bound (Theorem 10)
    maxPeriod = getMaxPeriod(chain) # Get the largest task period

    periodSum = 0
    for task in chain:
        periodSum = periodSum + task.period

    latencyBound = periodSum + maxPeriod

    return latencyBound

def optimalPhasing2kMaxHarm(chain):
    """ Function assigns optimal task phasing for (2,k)-max-harmonic periods 
        to minimize the end-to-end latency and returns the latency bound. 
    """

    max1Period = getMaxPeriod(chain)    # Get the largest task period
    max2Period = getMax2Period(chain)   # Get the secod largest period

    if is2kMaxHarmonic(chain) == False:
        print("max1Period: " + printTime(max1Period))
        print("max2Period: " + printTime(max2Period))

    assert is2kMaxHarmonic(chain)
    
    # Compute tasks where periods switch between max1 and max2
    nu = getPeriodSwitches(chain) 

    gamma = max1Period % max2Period

    tau_p = getFirstOccurance(chain, max1Period)

    # Set task phases to be optimal 
    if math.ceil(len(nu) / 2) * gamma >= max1Period:
        """ Phasing according to Eq. 46, 47 """
        offset = 0

        for task in chain:
            task.offset = offset

            offset = offset + task.period
    else:
        """ Phasing according to Eq. 48, 49 """
        offset = 0

        for task in chain:
            task.offset = offset
            
            if (task.period == max1Period) and (task != tau_p) and (task in nu):
                task.offset = task.offset + gamma
                offset = offset + gamma
                
            offset = offset + task.period
    
    # Compute the latency bound (Eq. 34)

    # Compute the sum of all periods
    periodSum = 0
    for task in chain:
        periodSum = periodSum + task.period

    latencyBound = periodSum + max1Period + min(max1Period, math.ceil(len(nu) / 2) * gamma)

    return latencyBound

def getFirstOccurance(chain, period):
    """ Return the task with T == period that has the lowest index in the chain (i.e. the first occurance). """

    for task in chain:
        if task.period == period:
            return task

def getPeriodSwitches(chain):
    """ Function returns the tasks that appear after a switch between T^E_{max,1} and T^E_{max,2}."""
    nu = []

    max1Period = getMaxPeriod(chain)    # Get the largest task period
    max2Period = getMax2Period(chain)   # Get the secod largest period

    # Compute how often periods switch between max1 and max2

    lastFound = 0
    for task in chain:
        if task.period == max1Period:
            if lastFound == max2Period:
                nu.append(task)
            lastFound = max1Period

        if task.period == max2Period:
            if lastFound == max1Period:
                nu.append(task)
            lastFound = max2Period

    return nu

if __name__ == '__main__':
    """ Debugging """
    os.system('cls' if os.name == 'nt' else 'clear')    # Clear the terminal
    # 创建三个任务，周期分别为 4ms, 12ms, 6ms
    # task1 = Task('Task1', mseconds(4), mseconds(4), mseconds(4), mseconds(0))
    # task2 = Task('Task2', mseconds(12), mseconds(12), mseconds(12), mseconds(0))
    # task3 = Task('Task3', mseconds(6), mseconds(6), mseconds(6), mseconds(0))

    # task1 = Task('Task1', mseconds(4), mseconds(4), mseconds(4), mseconds(0))
    # task2 = Task('Task2', mseconds(6), mseconds(6), mseconds(6), mseconds(0))
    # task3 = Task('Task3', mseconds(12), mseconds(12), mseconds(12), mseconds(0))

    # task1 = Task('Task1', mseconds(8), mseconds(8), mseconds(8), mseconds(0))
    # task2 = Task('Task2', mseconds(8), mseconds(8), mseconds(8), mseconds(0))
    # task3 = Task('Task3', mseconds(8), mseconds(8), mseconds(8), mseconds(0))

    # task1 = Task('Task1', mseconds(4), mseconds(4), mseconds(4), mseconds(0))
    # task2 = Task('Task2', mseconds(10), mseconds(10), mseconds(10), mseconds(0))
    # task3 = Task('Task3', mseconds(20), mseconds(20), mseconds(20), mseconds(0))

    
    # task1 = Task('Task1', mseconds(10), mseconds(10), mseconds(10), mseconds(0))
    # task2 = Task('Task2', mseconds(20), mseconds(20), mseconds(20), mseconds(0))
    # task3 = Task('Task3', mseconds(50), mseconds(50), mseconds(50), mseconds(0))

    t1 = 8  
    t2 = 12 
    t3 = 12

    task1 = Task('Task1', mseconds(t1), mseconds(t1), mseconds(t1), mseconds(0))
    task2 = Task('Task2', mseconds(t2), mseconds(t2), mseconds(t2), mseconds(0))
    task3 = Task('Task3', mseconds(t3), mseconds(t3), mseconds(t3), mseconds(0))

    # 将任务组成一个任务链
    chain = [task1, task2, task3]

    # print("=== 任务链信息 ===")
    # print(chainString(chain))  # 输出: 4.0 ms/0.0 ms -> 12.0 ms/0.0 ms -> 6.0 ms/0.0 ms

    # 检查是否满足 max-harmonic（最大调和）条件
    # Max-harmonic: 最大周期能被所有其他周期整除
    is_max = isMaxHarmonic(chain)
    print(f"是否为 Max-Harmonic: {is_max}")

    # 检查是否满足 (2,k)-max-harmonic 条件
    is_2k_max = is2kMaxHarmonic(chain)
    print(f"是否为 (2,k)-Max-Harmonic: {is_2k_max}")

    print("\n=== 方案 1: 同步发布（Synchronous Release）===")
    # 方案1：所有任务同时开始（offset = 0）
    dpt = DPT(chain)
    dpt.getDpt()
    sync_latency = dpt.maxAge
    print(f"端到端延迟: {printTime(sync_latency)}")

    print("\n=== 方案 2: 最优任务分段（Optimal Phasing）===")
    # 方案2：使用最优任务分段来最小化延迟

    # 先检查周期关系
    max_period = getMaxPeriod(chain)  # 12ms
    max2_period = getMax2Period(chain)  # 6ms
    print(f"最大周期: {printTime(max_period)}")
    print(f"第二大周期: {printTime(max2_period)}")

    if is_max:
        # 如果是 Max-Harmonic，使用 optimalPhasingMaxHarm
        opt_latency = optimalPhasingMaxHarm(chain)
        print(f"使用 Max-Harmonic 最优分段")
    else:
        # 如果不是 Max-Harmonic，使用 optimalPhasing2kMaxHarm
        opt_latency = optimalPhasing2kMaxHarm(chain)
        print(f"使用 (2,k)-Max-Harmonic 最优分段")

    print(f"端到端延迟: {printTime(opt_latency)}")

    print("\n=== 最优分段结果 ===")
    for task in chain:
        print(f"{task.name}: offset = {printTime(task.offset)}")

    print("\n=== 性能对比 ===")
    improvement = (sync_latency - opt_latency) / sync_latency * 100
    print(f"同步发布延迟: {printTime(sync_latency)}")
    print(f"最优分段延迟: {printTime(opt_latency)}")
    print(f"改进比例: {improvement:.1f}%")