import os
import random
import hashlib

def pickhalf(objects):
    '''
    Randomly pick half of the objects
    '''
    return random.sample(objects, len(objects)/2)

def pickmost(objects):
    '''
    Randomly pick 9/10 of the objects
    '''
    return random.sample(objects, len(objects)-len(objects)/10)

def toss():
    '''
    Coin toss
    '''
    return bool(random.randrange(2))

def tosshigh():
    '''
    High probability coin toss (9 of 10)
    '''
    return bool(random.randrange(10))

def tosslow():
    '''
    Low probability coin toss (1 of 10)
    '''
    return not bool(random.randrange(10))

def randhash():
    '''
    Returns random sha1 hash
    '''
    return hashlib.sha1(os.urandom(30)).hexdigest()
