"""
This file implements a class to represent a task, as well as functionality top generate 
random tasks and chains based on different settings.

Random chain generation:
* generateRandomTasks(...)            -> Random chains with automotive periods
* generateRandomTasks2kMax(...)       -> Random chains with (2,k)-max-harmonic periods
* generateRandomTasksMaxHarmonic(...) -> Random chains with max-harmonic periods
"""

from Time import *
from drs import drs
import random
import math

class Task:
    """ Class to represent a periodic task """

    def __init__(self, task_name, task_wcet, task_period, task_deadline, task_offset, task_priority = 0):
        self.name = task_name           # Task name
        self.wcet = task_wcet           # Worst-Case Execution Time of the task
        self.period = task_period       # Period of the task
        self.deadline = task_deadline   # Deadline of the task
        self.offset = task_offset       # Offset of the task
        self.priority = task_priority   # Priority of the task
        self.responseTime = 0           # Response time of the task

    def utilization(self):
        """ Returns the task utilization """
        return self.wcet / self.period
    
    def __str__(self):
        """ Print task information. """
        return "Task: %s, T=%s, C=%s, D=%s, O=%s, P=%s, RT=%s" % (self.name, printTime(self.period), printTime(self.wcet), printTime(self.deadline), printTime(self.offset), self.priority, self.responseTime)
    
    def getJobsUntil(self, until):
        """ Returns a list of jobs that are released between 0 and until. """
        count = math.ceil(until / self.period)

        jobs = []

        for j in range(0,count,1):
            tmpJob = Job(self, j)
            jobs.append(tmpJob)

        return jobs

class Job:
    """ Class to represent a job/instance of a task. """
    def __init__(self, job_task, job_id):
        self.task = job_task                                            # Task the job belongs to
        self.id = job_id                                                # ID of the job, starting with 0
        self.release = (self.id * self.task.period) + self.task.offset  # Release time of the job
        self.deadline = self.release + self.task.deadline               # Deadline of the job

    def __str__(self):
        """ Print job information. """
        return "Job(%s, %s): r = %s, d = %s" % (self.task.name, self.id, printTime(self.release), printTime(self.deadline))

def generateRandomTasks(count, utilization):
    """ Function to generate a set of random tasks based on the automotive periods """
    tasks = []
    periods = [1, 2, 5, 10, 20, 50, 100, 200, 1000] # Periods from "Real world automotive benchmark for free" WATERS 2015

    utilizations = drs(count, utilization)
    id = 0

    for u in utilizations:
        period = mseconds(random.choice(periods))
        wcet = math.ceil((u * period) / 1)
        
        tasks.append(Task("Task_%s" % (id), wcet, period, period, 0))
        id += 1

    frac, i = math.modf(tasksetUtilization(tasks) * 100)
    # Commented the check since we only need periods.
    #assert (i == utilization * 100)   # Make sure the utilization is correct on two decimals

    return tasks

def generateRandomTasks2kMax(count, utilization, k, numPeriods, maxAllowedPeriod):
    """ Function to generate a set of random tasks with random (2,k)-max harmonic periods. """
    generatedTasks = False

    while(generatedTasks == False):
        tasks = []
        periods = generatePeriodSet(k, numPeriods, maxAllowedPeriod)    # Generates random periods that are (2,k)-max harmonic
        
        utilizations = drs(count, utilization)
        id = 0

        for u in utilizations:
            period = mseconds(random.choice(periods))
            wcet = math.ceil((u * period) / 1)
            
            tasks.append(Task("Task_%s" % (id), wcet, period, period, 0))
            id += 1

        frac, i = math.modf(tasksetUtilization(tasks) * 100)
        # Commented the check since we only need periods.
        #assert (i == utilization * 100)   # Make sure the utilization is correct on two decimals

        if is2kMaxHarmonic(tasks) == True:  # Double check that the generated chain is (2,k)-max harmonic
            generatedTasks = True

    return tasks

def generateRandomTasksMaxHarmonic(count, utilization, numPeriods, maxAllowedPeriod):
    """ Function to generate a set of random tasks with random max harmonic periods. """
    generatedTasks = False

    while(generatedTasks == False):
        tasks = []
        periods = generateMaxHarmonicPeriodSet(numPeriods, maxAllowedPeriod)    # Generates random periods that are (2,k)-max harmonic
        
        utilizations = drs(count, utilization)
        id = 0

        for u in utilizations:
            period = mseconds(random.choice(periods))
            wcet = math.ceil((u * period) / 1)
            
            tasks.append(Task("Task_%s" % (id), wcet, period, period, 0))
            id += 1

        frac, i = math.modf(tasksetUtilization(tasks) * 100)
        # Commented the check since we only need periods.
        #assert (i == utilization * 100)   # Make sure the utilization is correct on two decimals

        if isMaxHarmonic(tasks) == True:  # Double check that the generated chain is (2,k)-max harmonic
            generatedTasks = True

    return tasks

def tasksetUtilization(tasks):
    """ Function to compute the utilization of a taskset. """
    utilization = 0.0

    for t in tasks:
        utilization += t.utilization()

    return utilization

def isMaxHarmonic(tasks):
    """ Function returns true of the task set is max harmonic. I.e. the largest task period can be evenly divided by all other periods. """

    # Get the largest period in the task set
    maxPeriod = getMaxPeriod(tasks)

    # Check if all periods evenly divide the largest task period
    for t in tasks:
        if maxPeriod % t.period != 0:
            return False

    return True

def getMaxPeriod(tasks):
    """ Function returns the largest task period. """
    maxPeriod = 0
    for t in tasks:
        if t.period > maxPeriod:
            maxPeriod = t.period
    
    return maxPeriod

def getMax2Period(tasks):
    """ Function returns the second largest period (or 0). """
    max1Period = 0
    max2Period = 0

    for t in tasks:
        if t.period > max1Period:
            max2Period = max1Period
            max1Period = t.period
        elif t.period < max1Period:
            if t.period > max2Period:
                max2Period = t.period
    
    return max2Period

def hyperperiod(tasks):
    """ Returns the hyperperiod of the taskset """
    periods = []

    for t in tasks:
        if not t.period in periods:
            periods.append(t.period)
    
    return math.lcm(*periods)

def chainString(chain):
    """ Helper to get a string representing the task chain. """
    retval = printTime(chain[0].period) + "/" + printTime(chain[0].offset)

    for task in chain[1:]:
        retval = retval + ' -> ' + printTime(task.period) + "/" + printTime(task.offset)

    return retval

def generatePeriodSet(k, numPeriods, maxAllowedPeriod):
    """ Generates (2,k)-max harminc period sets with configurable number of periods and a bound on the maximum allowed period."""
    periodSets = []

    # Compute all T^E_{max,2} candidates.
    tmax2Candidates = []
    for tmax1 in range(1,maxAllowedPeriod+1):
        tmax2 = getTmax2(k, tmax1)
        if tmax2 is not None:
            tmax2Candidates.append([tmax2, tmax1])
    
    # For each tmax1 and tmax2, we find all possible othe rperiod values.
    for tmax2, tmax1 in tmax2Candidates:

        # This can be done nicer, just to test...
        tmpPeriodSet = [tmax1, tmax2]

        for i in range(1,(tmax1%tmax2) + 1):
            if tmax1 % i == 0 and tmax2 % i == 0:
                tmpPeriodSet.append(i)

        if len(tmpPeriodSet) >= numPeriods:
            periodSets.append(tmpPeriodSet)

    index = random.randrange(len(periodSets))   # Pick a random period set out of all generated sets
    set = sorted(periodSets[index], key=int)    # Sort the periods

    return set

def getTmax2(k, tmax1):
    """ Computes T^E_{max,2} based on a given value of k and T^E_{max,1}. If the value is not an integer, None is returned. """
    if (2 * int(tmax1)) % int(k) == 0:
        return int((2 * int(tmax1)) / int(k))
    return None

def is2kMaxHarmonic(tasks):
    """ Test if a set of periods is (2,k)-max harmonic. """

    periods = []

    # Get all individual task periods
    for task in tasks:
        if task.period not in periods:
            periods.append(task.period)

    sortedPeriods = sorted(periods, key=int)

    hp = hyperperiod(tasks)

    max1 = sortedPeriods[len(sortedPeriods)-1]
    max2 = sortedPeriods[len(sortedPeriods)-2]

    if max1 * 2 != hp:          # for (2,k)-max harmonic task sets max1 * 2 must be equal to the hyperperiod
        return False
    
    if (hp / max2) % 1 != 0:    # For (2,k)-max harmonic task sets, max2 * k must be equal to the hyperperiod, and k must be integer
        return False
    
    for index in range(0, len(sortedPeriods)-2):   # don't check the two largest periods
        if max1 % sortedPeriods[index] != 0 or max2 % sortedPeriods[index] != 0:
            return False
    return True

def generateMaxHarmonicPeriodSet(numPeriods, maxAllowedPeriod):
    """
    Function generates a random period set with at least numPeriods periods. The maximum allowed period is 
    maxAllowedPeriod. During the generation, all possible period sets are generates that have 
    a length of at least numPeriods. From those the final periods will be selected.
    """
    allSets = []
    for i in range(1,maxAllowedPeriod+1):
        tmpSet = []
        for k in range(1, i+1):
            if i % k == 0:
                tmpSet.append(k)
        if len(tmpSet) >= numPeriods:
            allSets.append(tmpSet)
    
    index = random.randrange(len(allSets))
    set = sorted(allSets[index], key=int)

    return set

if __name__ == '__main__':
    """ Debugging """

    for i in range(0,10000):
        periods = generatePeriodSet(3, 5, 500)

        print(periods)

        # tasks = generateRandomTasks2kMax(5, 0.5, 7, 5, 500) #count, utilization, k, numPeriods, maxAllowedPeriod
        # print("--------------------------")
        # for task in tasks:
        #     print(str(task.period))
        # print("--------------------------")
        # assert is2kMaxHarmonic(tasks)
