""" 
This file implements the analysis of the paper:
Matthias Becker, Dakshina Dasari, Saad Mubeen, Moris Behnam, Thomas Nolte,
"Synthesizing job-level dependencies for automotive multi-rate effect chains", 
22nd IEEE International Conference on Embedded and Real-Time Computing Systems 
and Applications (RTCSA)

In addition: 
- The data age is computed under consideration of the time the
  value is present at the end of the chain (i.e. before it gets overwritten).
- Offsets are accounted for.
- LET semantics are used for communication.
 
Assumptions: 
- Periodic tasks with implicit deadlines and offset.
- LET semantics for communication.
"""
from Time import *
from Task import *
import networkx as nx
import os

class DPT:
    """ Class to represent a data propagation tree. """
    
    def __init__(self, chain):
        self.chain = chain  # Chain to analyse
        self.maxAge = None  # Maximum data age of the chain
        self.dpts = {}      # Data propagation tree (for each initial/root job)
        self.jobs = []      # All possible jobs that can be in the DPT (except the root jobs)
        self.dbg = False    # Flag to print debug information

        if self.dbg:
            print("Chain: ")
            for t in self.chain:
                print(t)

    def getRootJobs(self):
        """ Returns all root jobs of the chain. """

        rootTask = self.chain[0]
        hp = hyperperiod(self.chain)

        return rootTask.getJobsUntil(hp)

    def davareBound(self):
        """ Davare et al. bound without response times. """
        davare = 0

        for t in self.chain:
            davare += (t.period + t.deadline)

        return davare

    def getDpt(self):
        """ Returns the data propagation tree for all root jobs. """

        rootJobs = self.getRootJobs()

        # Create the list of jobs that must be considered for the analysis
        # The maximum time to consider can be upper bounded by the Davare bound and the release of the last 
        # root job (i.e. the last root job experiences the max data age).
        maxTime = self.davareBound() + rootJobs[-1].release    # The last root job experiences the max data age
        
        for t in self.chain[1:]:
            tmpJobs = []
            for j in t.getJobsUntil(maxTime):
                tmpJobs.append(DptJob(j))
            self.jobs.append(tmpJobs)

        # Construct the DPT for each root job
        for r in rootJobs:
            root = DptJob(r)                                        # Create the root job
            self.dpts[root] = nx.DiGraph()                          # Add the new graph to the dict with the root job as key
            self.dpts[root].add_node(root)                          # Add the root job to the graph
            dpt = self.recursiveDptBuild(self.dpts[root], root)     # Recursively construct the graph

        return self.dpts
     
    def recursiveDptBuild(self, graph, vertex):
        """ Recursively computes the data propagation tree. """
        
        # Check if the end of the chain is reached
        if self.chain.index(vertex.job.task) == len(self.chain) - 1:
            root = list(self.dpts.keys())[list(self.dpts.values()).index(graph)]    # Get the root node of this DPT    
            #vertex.branchAge = vertex.ri[1] + vertex.job.task.wcet - root.ri[0]     # Set the data age of this branch
            vertex.branchAge = vertex.di[1] - root.ri[0]                            # Set the data age of this branch. Data age is counted from initial sampling until the value at the end of the job is overwritten.

            if self.maxAge is None or self.maxAge < vertex.branchAge:
                self.maxAge = vertex.branchAge

            if self.dbg:
                self.printNode(vertex)           # Print helper to plot the DPT in the terminal
        else:

            if self.dbg:
                self.printNode(vertex)           # Print helper to plot the DPT in the terminal

            successors = self.getSuccessors(vertex)

            for successor in successors:
                if successor.ri[0] < vertex.di[0]:  # If the read interval of the successor starts before the data is first available, move it (only for this branch)
                    successor.ri[0] = vertex.di[0]
                    successor.di[0] = successor.ri[0] + successor.job.task.wcet
                
                # Append job to graph
                graph.add_node(successor)            # Add the next node to the graph
                graph.add_edge(vertex, successor)    # Add the edge to the new node

                # Build next edge by recursively calling recursiveDptBuild()
                self.recursiveDptBuild(graph, successor)
                
                # Reset intervals of the job (as it might be used in other branches of the DPT)
                successor.resetIntervals()

    def getSuccessors(self, writeJob):
        """ Returns the list of possible successor jobs """
        successors = []
        index = self.chain.index(writeJob.job.task)
        taskJobs = self.jobs[index] # We are interested in jobs of the next task in the chain. This is never called for the last task in the chain

        for readJob in taskJobs:
            if readJob.ri[1] >= writeJob.di[0] and readJob.ri[0] < writeJob.di[1]:  # Eq. 1 Becker RTCSA'16
                successors.append(readJob)
        
        return successors

    def printNode(self, node):
        pos = self.chain.index(node.job.task)    # Get the position of the associated task in the chain

        logStr = ""

        for x in range(0, pos):
            logStr += "   "
        logStr += "|--- %s" % node

        print(logStr)
        
class DptJob:
    """ Class to represent one job of the DPT. """

    def __init__(self, job):
        self.job = job                                                                  # The task job associated with this dpt node
        self.ri = [job.release, job.release]                                            # The read interval of the job (i.e. when data might be read). According to LET semantics! 
        self.di = [job.release + job.task.period, job.release + (2*job.task.period)]    # The data interval of the job (i.e. when data produced can be available). According to LET semantics! 
        self.branchAge = None                                                           # This is only set for leave nodes of the DPT

    def resetIntervals(self):
        """ Reset the read and data intervals (after they have been modified during the graph build). """
        self.ri = [self.job.release, self.job.release]                                                          # The read interval of the job (i.e. when data might be read). 
        self.di = [self.job.release + self.job.task.period, self.job.release + (2 * self.job.task.period)]      # The data interval of the job (i.e. when data produced can be available).

    def __str__(self):
        if not self.branchAge is None:
            return str(self.job) + " RI=[%s, %s] DI=[%s, %s) -> Age=%s" % (printTime(self.ri[0]), printTime(self.ri[1]), printTime(self.di[0]), printTime(self.di[1]), printTime(self.branchAge))
        else:
            return str(self.job) + " RI=[%s, %s] DI=[%s, %s)" % (printTime(self.ri[0]), printTime(self.ri[1]), printTime(self.di[0]), printTime(self.di[1]))

    __repr__ = __str__

if __name__ == '__main__':
    """ Debugging """
    os.system('cls' if os.name == 'nt' else 'clear')    # Clear the terminal

    task1 = Task('Task1', useconds(1), mseconds(10), mseconds(10), 0)
    task2 = Task('Task2', useconds(1), mseconds(1), mseconds(1), 0)
    task3 = Task('Task3', useconds(1), mseconds(10), mseconds(10), mseconds(1))

    chain = [task1, task2, task3]

    dpt = DPT(chain)
    dpt.dbg = True
    dpt.getDpt()

    print("Max Data Age = %s" % (printTime(dpt.maxAge)))

    task1 = Task('Task1', useconds(1), mseconds(10), mseconds(10), 0)
    task2 = Task('Task2', useconds(1), mseconds(50), mseconds(50), 0)
    task3 = Task('Task3', useconds(1), mseconds(10), mseconds(10), 0)
    task4 = Task('Task4', useconds(1), mseconds(50), mseconds(50), 0)

    chain = [task1, task2, task3, task4]

    dpt = DPT(chain)
    dpt.dbg = True
    dpt.getDpt()

    print("Max Data Age = %s" % (printTime(dpt.maxAge)))