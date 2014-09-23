from __future__ import print_function
from copy import deepcopy
from copy import copy
from random import randint
from random import choice
from structures import *
from datetime import time, timedelta

import logging


def morning_class(course, this_week):
    #Find course returns a list of time slots, but they should all be at the same time
    holds = this_week.find_course(course)[0].start_time < time(12, 0)
    return 1 if holds else 0


known_funcs = {"morning_class", morning_class}

class Constraint:
    def __init__(self, name, weight, func, course = None):
        if type(name) is not str:
            logging.error("Name is not a string")
            print("Name is not a string")
            return
        
        if type(weight) is not int:
            logging.error("Weight is not a string")
            print("Weight is not a string")
            return

        if not hasattr(func, '__call__'):
            if type(func) is str and not known_funcs.has_key(func):
                logging.error("Func string passed is not known")
                print("Func string passed is not known")
                return
            else:
                logging.error("Func passed is not a function")
                print("Func passed is not a function")
                return

        if not isinstance(course, Course):
            logging.error("Course is not of object type course")
            print("Course is not of object type course")
            return

        self.name = name
        self.weight = weight
        self.course = course
        if type(func) is str:
            self.func = func
        else:
            self.func = func

    def get_fitness(self, this_week):
        if self.course == None:
            return self.func(this_week) * self.weight
        else:
            return self.func(self.course, this_week) * self.weight


class Scheduler:
    """Schedules all courses for a week"""
    def __init__(self, courses, rooms, time_slots, time_slot_divide):
        #eventually will include mwf and tr slots instead of general slots
        logging.debug("Scheduler init")
        if type(courses) is list:
            if not isinstance(courses[0], Course):
                logging.error("Courses is not a list of Course objects")
                print("Courses is not a list of Course objects")
                return
        else:
            logging.error("Courses is not a list")
            print("Courses is not a list")
            return

        if type(rooms) is not list:
            logging.error("Rooms is not a list")
            print("Rooms is not a list")
            return

        #self.time_slots_mwf = time_slots_mwf
        #self.time_slots_tr = time_slots_tr
        self.time_slots = time_slots
        self.slot_divide = time_slot_divide
        self.courses = courses
        self.rooms = rooms
        self.weeks = [Week(rooms, self), Week(rooms, self), Week(rooms, self),
                      Week(rooms, self), Week(rooms, self)]
        self.constraints = []
        self.max_fitness = 0
        
        #Number of courses
        self.num_courses = len(courses)
        #Courses grouped by credit hours
        self.separated = self.separate_by_credit(self.courses)

    def separate_by_credit(self, courses_list):
        """Groups the courses based on number of credit hours.
        IN: list of course objects
        OUT: dictionary with keys=credit hours and values=list of course objects"""
        courses_by_credits = {}
        for each_course in courses_list:
            #Case 1: New key-value pair (make new list)
            if each_course.credit not in courses_by_credits.keys():
                courses_by_credits[each_course.credit] = [each_course]
            #Case 2: Add to value's list for key
            else:
                courses_by_credits[each_course.credit].append(each_course)
        return courses_by_credits


    def add_constraint(self, name, weight, func, course = None):
        self.constraints.append(Constraint(name, weight, func, course)) 
        self.max_fitness += weight
    

    def calc_fitness(self, this_week):
        """Calculates the fitness score of a schedule"""
        total_fitness = 0
        for each_constraint in self.constraints:
            total_fitness += each_constraint.get_fitness(this_week)

        this_week.fitness = total_fitness


    def mutate(self, func):
        """Mutates a schedule given an appropriate function"""
        if not hasattr(func, '__call__'):
            logging.error("Func passed is not a function")
            print("Func passed is not a function")
        

    def find_respective_time_slot(self, time_slot, week):
        """Finds the given time slot object in given week and returns it"""
        day = time_slot.info("Day")
        room = time_slot.info("Room")
        return week.find_time_slot(day, room, time_slot)


    def swap(self, course1, course2, schedule):
        """Performs swaps around 2 courses in a schedule
        IN: 2 Course objects, schedule object
        OUT: schedule object with swap performed"""
        pass


    def list_time_slots_for_week(self, week):
        """Gives list of all time slot objects in week while indexing them"""
        list_of_slots = []
        #index counters
        day = 0
        room = 0
        slot = 0
        
        for each_day in week.days:
            for each_room in each_day.rooms:
                for each_slot in each_room.schedule:
                    list_of_slots.append(each_slot)
                    each_slot.set_indices(day, room, slot)
                    slot += 1
                room += 1
                slot = 0
            day += 1
            room = 0
        return list_of_slots


    def find_time_slots_from_cuts(self, this_week, slots_list):
        """For a given week, returns all time slots matching the slots list"""
        matching_slots = []

        #form times from slots_list
        times = []
        for each_slot in slots_list:
            #todo: Condense this
            start, end = each_slot.split('-')
            start = start.split(':')
            start = list(map(int, start))
            start = time(start[0], start[1])
            times.append(start) #only care about start times right now
        
        full_list = self.list_time_slots_for_week(this_week)
        for each_slot in full_list:
            if each_slot.start_time in times:
                matching_slots.append(each_slot)
        return matching_slots


    def replace_time_slots(self, slotsA, slotsB):
        """Change all courses for matching time slots"""
        for i in slotsA:
            for j in slotsB:
                if i.start_time == j.start_time and i.room.number == j.room.number and \
                   i.room.day.day_code == j.room.day.day_code:
                    courseA = i.course
                    courseB = j.course
                    i.set_course(courseB)
                    j.set_course(courseA)
        return


    def assess_inconsistencies(self, this_week):
        """Returns a dictionary of surplus and lacking courses for a schedule/week
        IN: week object
        OUT: dictionary with keys surplus and lacking; former value is list of
             surplus time slots to be overridden; latter is list of courses not
             scheduled for the week"""
        #for future reference, ideally not mark subsequent matches as excess,
        #but rather assess on all possibilities
        counter = 0
        days = ['m', 't', 'w', 'r', 'f']
        seen = [0] * len(self.courses)
        inconsistencies = {'surplus': [], 'lacking': []}
        full_list = self.list_time_slots_for_week(this_week)

        for course in self.courses:
            markers = [0] * 5 #day markers
            for each_slot in full_list:
                if each_slot.course is not None:
                    if each_slot.course.code == course.code:
                        #update day marker
                        for i in range(len(days)):
                            if each_slot.room.day.day_code == days[i]:
                                markers[i] += 1
                        #credit-based logic
                        if course.credit == 1:
                            #if seen before, add to surplus
                            if seen[counter] > 0:
                                inconsistencies['surplus'].append(each_slot)
                            #any time seen, increment counter
                            seen[counter] += 1
                        elif course.credit == 3:
                            #seen
                            if seen[counter] > 0:
                                inconsistencies['surplus'].append(each_slot)
                            #not seen
                            else:
                                #complete mwf/tr found
                                if (markers[0] and markers[2] and markers[4]) or \
                                   (markers[1] and markers[3]):
                                    #increment seen
                                    seen[counter] = 1
                        elif course.credit == 4:
                            #seen
                            if seen[counter] > 0:
                                inconsistencies['surplus'].append(each_slot)
                            #not seen
                            else:
                                #complete mtwf/mwrf found
                                if (markers[0] and markers[1] and markers[2] and markers[4]) or \
                                   (markers[0] and markers[2] and markers[3] and markers[4]):
                                    #increment seen
                                    seen[counter] = 1
                        elif course.credit == 5:
                            #seen
                            if seen[counter] > 0:
                                inconsistencies['surplus'].append(each_slot)
                            #not seen
                            else:
                                #complete mtwrf found
                                if markers[0] and markers[1] and markers[2] and markers[3] and markers[4]:
                                    #increment seen
                                    seen[counter] = 1
            #assess lacking
            if seen[counter] == 0:
                inconsistencies['lacking'].append(self.courses[counter])
            counter += 1
            
        return inconsistencies


    def week_helper(self, time_slot, time_slot_list):
        """Gives the 5 timeslot objects and occupied status for each day in the same room,
        at the same time, with the same schedule/week as the given time slot object
        IN: list of time slot objects *for a schedule/week*, time slot object
        OUT: dictionary with occupied counter and unoccupied keys, with values being time slots
             for the week; also gives the objects in order by day and their occupation status
             in order by day"""
        helper = {'occupied': 0, 'unoccupied': [], 'in_order':[None, None, None, None, None],
                  'occupation':[0,0,0,0,0]}
        #Only need start time, not end time, because time slots on the same day don't overlap
        marker = False #marker for whether open or not for current
        this_time = time_slot.start_time
        this_room = time_slot.room.number
        for each_slot in time_slot_list:
            if each_slot.start_time == this_time and each_slot.room.number == this_room:
                #occupation status
                if each_slot.course is None:
                    marker = True
                    helper['unoccupied'].append(each_slot)
                else:
                    #occupied counter
                    helper['occupied'] += 1

                #day
                temp_day = each_slot.room.day.day_code
                if temp_day == 'm':
                    helper['in_order'][0] = each_slot
                    helper['occupation'][0] = 1 if marker else 0
                elif temp_day == 't':
                    helper['in_order'][1] = each_slot
                    helper['occupation'][1] = 1 if marker else 0
                elif temp_day == 'w':
                    helper['in_order'][2] = each_slot
                    helper['occupation'][2] = 1 if marker else 0
                elif temp_day == 'r':
                    helper['in_order'][3] = each_slot
                    helper['occupation'][3] = 1 if marker else 0
                else:
                    helper['in_order'][4] = each_slot
                    helper['occupation'][4] = 1 if marker else 0
                marker = False #reset it
        #cleanup...take care of cases where time slot has been removed
        for entry in helper['in_order']:
            if entry is None:
                #occupied counter
                helper['occupied'] += 1
        return helper


    def resolve_inconsistencies(self, this_week, inconsistencies):
        """Removes excess courses and adds lacking courses to week.
        IN: (crossed) week object, inconsistencies dict with surplus and lacking
             surplus is list of time slots; lacking is list of courses
        OUT: (crossed) week object that represents all courses once"""
        full_list = self.list_time_slots_for_week(this_week)
        open_list = []

        #free excess slots
        for each_slot in inconsistencies['surplus']:
            each_slot.course = None
        #find all excess slots
        for i in full_list:
            if i.course is None:
                open_list.append(i)
        #fill in missing courses
        self.randomly_fill_schedule(this_week, inconsistencies['lacking'], open_list)           


    def crossover(self, P1, P2):
        """Mixes weeks (schedules) P1 and P2 to create 2 children weeks, then corrects
        the children weeks as necessary
        IN: 2 parent schedules, P1 and P2
        OUT: 2 children schedules, C1 and C2, in a list"""
        output = []
        #the time slot(s) which will be moved between C1 and C2
        time_slots = self.time_slots[:self.slot_divide]

        C1 = P1.deep_copy()
        C2 = P2.deep_copy()
        #P1's slots to have its courses cloned on P2
        cutA = self.find_time_slots_from_cuts(C1, time_slots)
        #P2's slots to have its courses cloned on P1
        cutB = self.find_time_slots_from_cuts(C2, time_slots)
        #do the replacement
        self.replace_time_slots(cutA, cutB)
        
        for i in (C1, C2):
            #figure out what have extra of/don't have
            inconsistencies = self.assess_inconsistencies(i)
            #clear the excess; try to schedule lacking
            self.resolve_inconsistencies(i, inconsistencies)
            output.append(i)
        return output


    def breed(self):
        """Produces a set of schedules based of the current set of schedules"""
        #for x in range(15):
        #    self.weeks.append(Week(self.rooms, self))
        #for each_week in self.weeks:
        #    list_slots = self.list_time_slots_for_week(each_week)
        #    self.randomly_fill_schedule(each_week, self.courses, list_slots)
        if len(self.weeks) < 2:
            logging.error("Not enough weeks to breed")
            print("Not enough weeks to breed")
            return
        #combinations...(ex) 5 choose 2
        for each_week in range(len(self.weeks) - 1):
            for each_other_week in range(each_week + 1, len(self.weeks)):
                children = self.crossover(self.weeks[each_week], self.weeks[each_other_week])
                #add to list of weeks
                self.weeks.extend(children)


    def evolution_loop(self):
        """Main loop of scheduler, run to evolve towards a high fitness score"""
        fitness_baseline = 30
        total_iterations = 0
        counter = 0
        MAX_TRIES = 5 

        def week_slice_helper():
            self.weeks.sort(key=lambda x: x.fitness, reverse=True)
            self.weeks = self.weeks[:5]

        while True:
            print('Counter:', counter)
            for each_week in self.weeks:
                self.calc_fitness(each_week)
            print([i.fitness for i in self.weeks])

            week_slice_helper()
            if counter >= MAX_TRIES:
                print('Max tries reached; final output found')
                break

            print(min(i.fitness for i in self.weeks))
            if min(i.fitness for i in self.weeks) == self.max_fitness:
                break

            self.breed()
            total_iterations += 1 
            counter += 1

        print("Breeding iterations: ", total_iterations)


    def time_slot_available(self, day, first_time_slot):
        for room in day.rooms:
            if room.number != first_time_slot.room.number:
                continue

            for t_slot in room:
                if t_slot == first_time_slot and t_slot.course == None:
                    return (t_slot, True)
        
        return (None, False)


    def randomly_fill_schedule(self, week_to_fill, courses_list, list_slots_to_fill):
        """Fills in random schedule for given week, courses, and time slots"""

        #helper function
        def find_index(time_slot, time_slot_list):
            """Finds index of time slot object in list of time slots for week"""
            counter = 0
            for each_slot in time_slot_list:
                if each_slot.room.number == time_slot.room.number and \
                   each_slot.start_time == time_slot.start_time and \
                   each_slot.room.day.day_code == time_slot.room.day.day_code:
                   return counter
                counter += 1
            logging.error("Index not found")
            print("Index not found")
            return

        def assign_and_remove(course, time_slot, slots_list, week):
            """Assigns course to time slot and removes time slot from list of time slots"""
            temp_room_index = time_slot.room_index
            temp_day_index = time_slot.day_index
            temp_slot_index = time_slot.slot_index

            i = find_index(time_slot, slots_list)
            week.days[temp_day_index].rooms[temp_room_index].schedule[temp_slot_index].set_course(course)
            del(slots_list[i])

        courses_by_credits = self.separate_by_credit(courses_list)
        #print(courses_by_credits)
        #main loop
        each_week = week_to_fill #todo...change var names to input rather than this
        #Make list of all time slots for week
        list_of_time_slots = list_slots_to_fill #todo...change var names to input ...
        #5 hour case is easy because we handle it first...removes possibility of
        #selecting a week with courses
        try:
            for each_5 in courses_by_credits[5]:
                #Choose a random timeslot from the list of all time slots for week
                random_slot = choice(list_of_time_slots)
                temp_pool = deepcopy(list_of_time_slots)
                done = False
                while len(temp_pool) > 0 and not done:
                    possibilities = self.week_helper(random_slot, temp_pool)
                    #each day open for that time and room
                    if len(possibilities['unoccupied']) == 5:
                        for each_assignee in possibilities['in_order']:
                            assign_and_remove(each_5, each_assignee, list_of_time_slots, each_week)
                        done = True
                    #case that cannot schedule for this time and room
                    else:
                        #remove this timeslot and the other unoccupied in its week from temp pool
                        for to_remove in possibilities['unoccupied']:
                            i = find_index(to_remove, temp_pool)
                            del(temp_pool[i])
                        #get a new random time slot
                        random_slot = choice(temp_pool)
                #2 ways out of while...test for which
                if len(temp_pool) == 0 and not done:
                    #impossible to schedule
                    week_to_fill.valid = False
        except KeyError:
            pass
        #other cases must consider how the week is taken up
        try:
            for each_4 in courses_by_credits[4]:
                #Choose a random timeslot from the list of all time slots for week
                random_slot = choice(list_of_time_slots)
                temp_pool = deepcopy(list_of_time_slots)
                done = False
                while len(temp_pool) > 0 and not done:
                    #check rest of week's courses at same time and place (differ by day)
                    possibilities = self.week_helper(random_slot, temp_pool)
                    #case that whole week is open
                    if len(possibilities['unoccupied']) == 5:
                        for d in (0, 2, 4):
                            #MWF
                            assign_and_remove(each_4, possibilities['in_order'][d], list_of_time_slots, each_week)
                        #T or R
                        j = randint(0,1)
                        if j:
                            assign_and_remove(each_4, possibilities['in_order'][1], list_of_time_slots, each_week) #T
                        else:
                            assign_and_remove(each_4, possibilities['in_order'][3], list_of_time_slots, each_week) #R
                        done = True
                    #case that mwf and either t or r are open
                    elif possibilities['occupation'][0] and possibilities['occupation'][2] and \
                         possibilities['occupation'][4] and \
                         (possibilities['occupation'][1] or possibilities['occupation'][3]):
                        for d in (0, 2, 4):
                            #MWF
                            assign_and_remove(each_4, possibilities['in_order'][d], list_of_time_slots, each_week)
                        if possibilities['occupation'][1]:
                            assign_and_remove(each_4, possibilities['in_order'][1], list_of_time_slots, each_week)
                        else:
                            assign_and_remove(each_4, possibilities['in_order'][3], list_of_time_slots, each_week)
                        done = True
                    #case that cannot schedule for this time and room
                    else:
                        #remove this timeslot and the other unoccupied in its week from temp pool
                        for to_remove in possibilities['unoccupied']:
                            i = find_index(to_remove, temp_pool)
                            del(temp_pool[i])
                        #get a new random time slot
                        random_slot = choice(temp_pool)
                #2 ways out of while...test for which
                if len(temp_pool) == 0 and not done:
                    #impossible to schedule
                    week_to_fill.valid = False
        except KeyError:
            pass
        try:
            for each_3 in courses_by_credits[3]:
                #Choose a random timeslot from the list of all time slots for week
                random_slot = choice(list_of_time_slots)
                temp_pool = deepcopy(list_of_time_slots)
                done = False
                while len(temp_pool) > 0 and not done:
                    #check rest of week's courses at same time and place (differ by day)
                    possibilities = self.week_helper(random_slot, temp_pool)
                    #case that whole week is open...MWF or TR
                    if len(possibilities['unoccupied']) == 5:
                        j = randint(0,1)
                        #MWF
                        if j:
                            for d in (0, 2, 4):
                                assign_and_remove(each_3, possibilities['in_order'][d], list_of_time_slots, each_week)
                        #TR
                        else:
                            for d in (1, 3):
                                assign_and_remove(each_3, possibilities['in_order'][d], list_of_time_slots, each_week)
                        done = True
                    #case that mwf is open, but not tr
                    elif possibilities['occupation'][0] and possibilities['occupation'][2] and \
                         possibilities['occupation'][4]:
                        for d in (0, 2, 4):
                            assign_and_remove(each_3, possibilities['in_order'][d], list_of_time_slots, each_week)
                        done = True
                    #case that tr is open, but not mwf
                    elif possibilities['occupation'][1] and possibilities['occupation'][3]:
                        for d in (1, 3):
                            assign_and_remove(each_3, possibilities['in_order'][d], list_of_time_slots, each_week)
                        done = True
                    #case that cannot schedule for this time and room
                    else:
                        #remove this timeslot and the other unoccupied in its week from temp pool
                        for to_remove in possibilities['unoccupied']:
                            i = find_index(to_remove, temp_pool)
                            del(temp_pool[i])
                        #get a new random time slot
                        random_slot = choice(temp_pool)
                #2 ways out of while...test for which
                if len(temp_pool) == 0 and not done:
                    #impossible to schedule
                    week_to_fill.valid = False
        except KeyError:
            pass
        #Case of 1 hour is very easy because we saved it for last--just take whatever you find
        try:
            for each_1 in courses_by_credits[1]:
                assign_and_remove(each_1, random_slot, list_of_time_slots, each_week)
        #case of no 1 hour courses
        except KeyError:
            pass


    def generate_starting_population(self):
        """Generates starting population"""
        for x in range(5):
            self.weeks.append(Week(self.rooms, self))

        for each_week in self.weeks:
            list_slots = self.list_time_slots_for_week(each_week)
            self.randomly_fill_schedule(each_week, self.courses, list_slots)
            if not each_week.valid: #if impossible to generate (incomplete week)
                del self.weeks[self.weeks.index(each_week)]
        if len(self.weeks) == 0:
            logging.error("Could not schedule")
            print("Could not schedule")
            return

    '''def randomly_fill_schedules(self):
        #get all available time slots grouped by day
        for each_week in self.weeks:
            time_slots_by_day = dict([(day, list()) for day in "mtwrf"])
            for day in each_week.days:
                for room in day.rooms:
                    time_slots_by_day[day.day_code].extend([t for t in room])
            
            for courses_in_curr_credit in self.courses_by_credits.values()[::-1]:
                index = 0
                times_on_index = 0 
                while True:
                    if index == len(courses_in_curr_credit):
                        break

                    times_on_index += 1
                    each_course = courses_in_curr_credit[index]
                    day_schedule = ""
                    #if each_course.credit == 3
                    day_schedule = "tr" if random.randint(0,1) else "mwf"
                    if each_course.credit == 4:
                        day_schedule = "mtwf" if random.randint(0,1) else "mwrf"
                    elif each_course.credit == 5:
                        day_schedule = "mtwrf"

                    should_index = True
                    rand_time_slot = time_slots_by_day[day_schedule[0]][random.randint(0, len(time_slots_by_day[day_schedule[0]])-1)]
                    to_schedule_lyst = [rand_time_slot]
                    for day_code in day_schedule[1:]:
                        time_slot_to_schedule, time_found = self.time_slot_available(each_week[day_code], rand_time_slot)
                        to_schedule_lyst.append(time_slot_to_schedule) 
                        should_index = should_index and time_found 

                    if should_index or times_on_index > 10:
                        if times_on_index > 10:
                            #uncomment for output of bad courses
                            #print("Unable to schedule ", str(each_course))
                            pass
                        else:
                            for t_slot in to_schedule_lyst:
                                t_slot.course = each_course
                        index += 1
                        times_on_index = 1'''

                    

