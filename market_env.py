from random import random
import numpy as np
import math

import gym
from gym import spaces

class MarketEnv(gym.Env):

    PENALTY = 1 #0.999756079

    def __init__(self, filenames, scope = 60, sudden_death = -1., cumulative_reward = False):
        self.scope = scope
        self.sudden_death = sudden_death
        self.cumulative_reward = cumulative_reward

        self.targetCodes = []
        self.dataMap = {}

        for filename in filenames:
            data = {}
            lastClose = 0
            lastVolume = 0
            try:
                for line in open( filename, 'r' ):
                    if line.strip() != "":
                        dt, openPrice, high, close, low, volume = line.strip().split(",")
                        try:
                            if True: 
                                high = float(high) if high != "" else float(close)
                                low = float(low) if low != "" else float(close)
                                close = float(close)
                                volume = int(volume)

                                if lastClose > 0 and close > 0 and lastVolume > 0:
                                    close_ = (close - lastClose) / lastClose
                                    high_ = (high - close) / close
                                    low_ = (low - close) / close
                                    volume_ = (volume - lastVolume) / lastVolume
                                    
                                    data[dt] = (high_, low_, close_, volume_)

                                lastClose = close
                                lastVolume = volume
                        except Exception, e:
                            print e, line.strip().split(",")
                f.close()
            except Exception, e:
                print e

            self.dataMap[filename] = data
            self.targetCodes.append(filename)

        self.actions = [
            "LONG",
            "SHORT",
        ]

        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(np.ones(scope * (len(filenames) + 1)) * -1, np.ones(scope * (len(filenames) + 1)))

        self.reset()
        self._seed()

    def _step(self, action):
        if self.done:
            return self.state, self.reward, self.done, {}

        self.reward = 0
        if self.actions[action] == "LONG":
            if sum(self.boughts) < 0:
                for b in self.boughts:
                    self.reward += -(b + 1)
                if self.cumulative_reward:
                    self.reward = self.reward / max(1, len(self.boughts))

                if self.sudden_death * len(self.boughts) > self.reward:
                    self.done = True

                self.boughts = []

            self.boughts.append(1.0)
        elif self.actions[action] == "SHORT":
            if sum(self.boughts) > 0:
                for b in self.boughts:
                    self.reward += b - 1
                if self.cumulative_reward:
                    self.reward = self.reward / max(1, len(self.boughts))

                if self.sudden_death * len(self.boughts) > self.reward:
                    self.done = True

                self.boughts = []

            self.boughts.append(-1.0)
        else:
            pass

        vari = self.target[self.targetDates[self.currentTargetIndex]][2]
        self.cum = self.cum * (1 + vari)

        for i in xrange(len(self.boughts)):
            self.boughts[i] = self.boughts[i] * MarketEnv.PENALTY * (1 + vari * (-1 if sum(self.boughts) < 0 else 1))

        self.defineState()
        self.currentTargetIndex += 1
        if self.currentTargetIndex >= len(self.targetDates) or self.endDate <= self.targetDates[self.currentTargetIndex]:
            self.done = True

        if self.done:
            for b in self.boughts:
                self.reward += (b * (1 if sum(self.boughts) > 0 else -1)) - 1
            if self.cumulative_reward:
                self.reward = self.reward / max(1, len(self.boughts))

            self.boughts = []

        return self.state, self.reward, self.done, {"dt": self.targetDates[self.currentTargetIndex], "cum": self.cum, "code": self.targetCode}

    def _reset(self):
        r = int(random() * len(self.targetCodes))
        print self.targetCodes
        self.targetCode = self.targetCodes[r]
        self.target = self.dataMap[self.targetCode]
        self.targetDates = sorted(self.target.keys())
        self.currentTargetIndex = self.scope
        self.boughts = []
        self.cum = 1.

        self.done = False
        self.reward = 0

        self.defineState()

        return self.state

    def _render(self, mode='human', close=False):
        if close:
            return
        return self.state

    '''
    def _close(self):
        pass

    def _configure(self):
        pass
    '''

    def _seed(self):
        return int(random() * 100)

    def defineState(self):
        tmpState = []

        budget = (sum(self.boughts) / len(self.boughts)) if len(self.boughts) > 0 else 1.
        size = math.log(max(1., len(self.boughts)), 100)
        position = 1. if sum(self.boughts) > 0 else 0.
        tmpState.append([[budget, size, position]])

        subject = []
        subjectVolume = []
        for i in xrange(self.scope):
            try:
                subject.append([self.target[self.targetDates[self.currentTargetIndex - 1 - i]][2]])
                subjectVolume.append([self.target[self.targetDates[self.currentTargetIndex - 1 - i]][3]])
            except Exception, e:
                print self.targetCode, self.currentTargetIndex, i, len(self.targetDates)
                self.done = True
        tmpState.append([[subject, subjectVolume]])

        tmpState = [np.array(i) for i in tmpState]
        self.state = tmpState

