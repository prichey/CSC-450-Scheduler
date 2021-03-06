from __future__ import print_function
from copy import deepcopy
from copy import copy
from random import randint
from random import choice
from math import floor
from datetime import time, timedelta
from structures import *
from constraint import *
from time import time as now
from collections import Counter
import gc
import sys
sys.path.append("../")
import gui

#import interface # uncomment to use export_schedule_xml
import xml.etree.ElementTree as ET
import os.path

#gc.set_debug(gc.DEBUG_LEAK)


class SchedulerInitError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class BreedError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FilterError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class MalformedTimeslotError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)



class Scheduler:

    """Schedules all courses for a week"""

    def __init__(self, courses, rooms, time_slots_mwf, time_slots_tr, time_slot_divide, test = False):
        if type(courses) == list:
            if len(courses) != 0:
                if not all(isinstance(each_course, Course) for \
                        each_course in courses):
                   raise SchedulerInitError("Courses - Not all of type Course")
            else:
                raise SchedulerInitError("Courses - List has no elements")
        else:
            raise SchedulerInitError("Courses - Not a list")

        if type(rooms) == list:
            if len(rooms) != 0:
                if not all(isinstance(each_room, tuple) for each_room in rooms):
                    raise SchedulerInitError("Rooms - Not all tuple type")
                else:
                    for each_room in rooms:
                        if not all(isinstance(part, str) for part in each_room):
                            raise SchedulerInitError("Rooms - Not all parts are str type")
            else:
                 raise SchedulerInitError("Rooms - List has no elements")
        else:
            raise SchedulerInitError("Rooms - Not a list")

        if type(time_slots_mwf) == list:
            if len(time_slots_mwf) != 0:
                if not all(isinstance(each_slot, str) for \
                        each_slot in time_slots_mwf):
                    raise SchedulerInitError("Time Slot MWF - \
                            Not all string type")
            else:
                 raise SchedulerInitError("Time Slot MWF -\
                         List has no elements")
        else:
            raise SchedulerInitError("Time Slot MWF - Not a list")

        if type(time_slots_tr) == list:
            if len(time_slots_tr) != 0:
                if not all(isinstance(each_slot, str) for \
                        each_slot in time_slots_tr):
                    raise SchedulerInitError("Time Slot TR - \
                            Not all string type")
            else:
                 raise SchedulerInitError("Time Slot TR -\
                         List has no elements")
        else:
            raise SchedulerInitError("Time Slot TR - Not a list")

        self.time_slots_mwf = time_slots_mwf
        self.time_slots_tr = time_slots_tr
        self.time_slots = time_slots_mwf + time_slots_tr
        if type(time_slot_divide) == int:
            if time_slot_divide < 0 and \
                time_slot_divide >= min(len(self.time_slots_mwf),
                                        len(self.time_slots_tr)):
                raise SchedulerInitError("Time Slot Divide - Not valid number")
        else:
            raise SchedulerInitError("Time Slot Divide - Not valid number")

        self.slot_divide = time_slot_divide
        self.courses = courses
        self.rooms = rooms
        self.weeks = []

        self.constraints = []
        self.num_hard_constraints = 0  # updated in globs, used for the mandatory, hardcoded constraints
        self.max_fitness = 0
        self.rooms_avail = {}

        # default message to be displayed on the loading screen
        self.gui_loading_info = ""
        self.gui_loading_info1 = self.gui_loading_info2 = self.gui_loading_info3 = ""
        
        # allowing the user to pause the algorithm to check constraints
        self.paused = False
        self.time_left_to_run = 0
        self.saved_state_of_constraints = []

        #Courses separated by credit hours
        self.separated = self.separate_by_credit(self.courses)

    ## Groups courses based on credits
    #  @param self
    #  @param credit A credit object
    #  @return courses_by_credits 
    def separate_by_credit(self, courses_list):
        """Groups the courses based on number of credit hours.
        IN: list of course objects
        OUT: dictionary with keys=credit hours and values=list of course objects"""
        courses_by_credits = {}
        for each_course in courses_list:
            # Case 1: New key-value pair (make new list)
            if each_course.credit not in courses_by_credits.keys():
                courses_by_credits[each_course.credit] = [each_course]
            # Case 2: Add to value's list for key
            else:
                courses_by_credits[each_course.credit].append(each_course)
        return courses_by_credits

    ## Adds constraint to schedule
    #  @param self
    #  @param constraint A constraint object
    #  @return none
    def add_constraint(self, name, weight, func, args = [], universal = False):
        """Adds an constraint to the schedule"""
        try:
            exists = False
            for constraint in self.constraints:
                if constraint.name == name:
                    exists = True
            if not exists:
                self.constraints.append(Constraint(name, weight, func, args, universal))
                self.max_fitness += weight
        except:
            print("Constraint {0} could not be added".format(name))

    ## Clears constraints from list
    #  @param self
    #  @param  A constraint object
    #  @return none 
    def clear_constraints(self):
        """Removes all constraints from list"""
        self.constraints = []
        self.max_fitness = 0

        
    ## Removes list constraint from schedule
    #  @param self
    #  @param  A constraint object
    #  @return none     
    def delete_list_constraints(self, constraint_name_list):
        """Removes list constraints from schedule"""
        for constraint_name in constraint_name_list:
            if "Avail" in constraint_name or\
               "NotAvail" in constraint_name:
               self.delete_room_avail(constraint_name)
            for constraint_obj in self.constraints:
                if constraint_name == constraint_obj.name:
                    self.max_fitness -= constraint_obj.weight
                    self.constraints.remove(constraint_obj)
                    break

    ## Calculate the fitness score of a schedule
    #  @param self
    #  @param  A constraint object
    #  @return none 
    def calc_fitness(self, this_week):
        """Calculates the fitness score of a schedule"""
        total_fitness = 0
        number_valid = 0
        total_to_be_valid = 0
        for each_constraint in self.constraints:
            each_fitness = each_constraint.get_fitness(this_week)
            if not this_week.valid:
                break
            this_week.constraints[each_constraint.name] = [each_fitness["score"],
                    each_constraint.weight if each_constraint.weight != 0 else 1]
            if each_constraint.weight == 0:
                total_to_be_valid += 1
                number_valid += each_fitness["score"]
                #print(each_constraint.name)
            else:
                total_fitness += each_fitness["score"]

        this_week.fitness = total_fitness
        this_week.num_valid = number_valid

        #print(this_week.constraints)

    ## Safely adds room availability to scheduler
    # @param self
    # @param room A full name of a room (building + number, no spaces)
    # @param is_avail A boolean saying if it is or is not availabile
    # @param start A string representing time in format hh:mm
    # @param end A string representing time in format hh:mm
    def add_room_avail(self, room, is_avail, days, start, end):
        if not self.rooms_avail.has_key(room):
            self.rooms_avail[room] = []
            
        is_avail_char = '+' if is_avail else '-'
        self.rooms_avail[room].append((is_avail_char, days.lower(), start, end))
        print("self.rooms_avail updated to: ")
        print(self.rooms_avail)
        
     
    def delete_room_avail(self, constraint_name):
        tokens = constraint_name.split('_')
        tokens[1] = '+' if tokens[1] == "Avail" else '-'
        room = tokens[0]
        tokens = (tokens[1], tokens[4].lower(), tokens[2], tokens[3])

        
        if self.rooms_avail.has_key(room):
            this_room_avail = self.rooms_avail[room]
            for counter in range(len(this_room_avail)):
                if this_room_avail[counter] == tokens:
                    self.rooms_avail[room].pop(counter)
                    break
                    
        if not self.rooms_avail[room]:
            del self.rooms_avail[room]

    ## Mutates a schedule by changing one course based off a random constraint
    #  @param self
    #  @param this_week A week to modify
    def guided_mutate(self, this_week):
        # deep copy the week so we can't drop the fitness score
        copy_of_this_week = this_week.deep_copy()

        # get a list of all failed constraints
        failed_constraints = []
        for each_constraint in self.constraints:
            constraint_result = each_constraint.get_fitness(copy_of_this_week)
            if each_constraint.weight != 0 and \
               constraint_result["score"] != each_constraint.weight:
                failed_constraints.append((each_constraint, constraint_result))

        # randomly select a failed constraint
        total_failed = len(failed_constraints)
        if total_failed > 0:
            choice = randint(0, total_failed - 1)
            selected_constraint = failed_constraints[choice][1]
        else:
            print("No failed constraints")
            return

        # randomly select a course from the select constraint
        total_failed_courses = len(selected_constraint["failed"])
        if total_failed_courses > 0:
            selected_course = selected_constraint["failed"][randint(0, total_failed_courses - 1)]
        else:
            print("No courses for failed constraint")
            return

        print("Trying to improve: ", failed_constraints[choice][0].name)
        print("Trying to reschedule: ", selected_course)

        starting_len = len(selected_constraint["failed"])
        GUIDED_MAX_TRIES = 100
        guided_counter = 0
        while guided_counter < GUIDED_MAX_TRIES:
            # unschedule and then reschedule the course
            copy_of_this_week.unschedule_course(selected_course) 
            self.randomly_fill_schedule(copy_of_this_week, [selected_course], 
                                        copy_of_this_week.find_empty_time_slots())
    

            copy_of_this_week.valid = True # reset the valid so calc_fitness works correctly
            copy_of_this_week.update_sections(self.courses)
            self.calc_fitness(copy_of_this_week)
            result = failed_constraints[choice][0].get_fitness(copy_of_this_week)
            if len(result["failed"]) < starting_len and copy_of_this_week.valid:
                print("Rescheduled: ", selected_course)
                if len(result["failed"]) == 0:
                    break
                else:
                    total_failed_courses = len(result["failed"])
                    selected_course = result["failed"][randint(0, total_failed_courses - 1)]
                    guided_counter += 1
                    starting_len -= 1
                    print("Trying to reschedule: ", selected_course)
            else:
                guided_counter += 1

        # make sure we don't make things worse
        if copy_of_this_week.valid and copy_of_this_week.fitness >= this_week.fitness:
            print("Keeping mutant with: ", copy_of_this_week.fitness)
            self.weeks.append(copy_of_this_week)


    ## Mutates a schedule by changing the courses time
    #  @param self
    #  @param  A week to modify
    def mutate(self, this_week):
        """Mutates a schedule by changing a course's time"""
        empty_slots = this_week.find_empty_time_slots()
        if len(empty_slots) == 0:
            # no mutation performed
            return this_week

        roll = randint(1, len(self.courses) - 1)
        random_course = self.courses[roll]
        old_slots = this_week.find_course(random_course)
        for each_old_slot in old_slots:
            # No longer assigned
            each_old_slot.remove_course()
        # Reassign
        self.randomly_fill_schedule(this_week, [random_course], empty_slots)


    ## Provides all time slots matching in a given week
    #  @param self
    #  @param  A Function that finds all matching time slots
    #  @return matching_slots
    def find_time_slots_from_cuts(self, this_week, slots_list):
        """For a given week, returns all time slots matching the slots list"""
        matching_slots = []

        # form times from slots_list
        start_times = []
        end_times = []
        for each_slot in slots_list:
            start, end = each_slot.split('-')
            start = start.split(':')
            start = list(map(int, start))
            start = time(start[0], start[1])
            start_times.append(start)

            end = end.split(':')
            end = list(map(int, end))
            end = time(end[0], end[1])
            end_times.append(end)

        full_list = this_week.list_time_slots()
        for each_slot in full_list:
            if each_slot.start_time in start_times and\
               each_slot.end_time in end_times:
                matching_slots.append(each_slot)

        return matching_slots

    ## Swaps courses when a match is found in a given week
    #  @param self
    #  @param  A Function that swaps all matching time slots
    #  @return none
    def replace_time_slots(self, slotsA, slotsB):
        """Change all courses for matching time slots ("swaps")
        IN: two lists of time slots (cuts) for 2 weeks
        OUT: two lists have been 'swapped'"""
        for i in slotsA:
            for j in slotsB:
                if i.start_time == j.start_time and i.room.number == j.room.number and \
                   i.room.day.day_code == j.room.day.day_code:
                    courseA = i.course
                    courseB = j.course
                    i.set_course(courseB)
                    j.set_course(courseA)
        return

    ## Returns a dictionary for of reminder and lacking courses
    #  @param  self 
    #  @param  A Function that enables the user to see any inconsistencies
    #  @return inconsistencies
    def assess_inconsistencies(self, this_week):
        """Returns a dictionary of surplus and lacking courses for a schedule/week
        IN: week object
        OUT: dictionary with keys surplus and lacking; former value is list of
             courses with surplus; latter is list of courses not
             scheduled for the week"""
        inconsistencies = {'surplus': [], 'lacking': []}
        full_list = this_week.list_time_slots()

        for course in self.courses:
            slots = this_week.find_course(course)
            num_slots = len(slots)
            if num_slots == 0:
                inconsistencies['lacking'].append(course)
            elif num_slots > course.credit:
                inconsistencies['surplus'].append(course)

        return inconsistencies


    ## Removes excess courses and adds lacking courses to week 
    #  @param self
    #  @param  A Function that finds all matching time slots
    #  @return none
    def resolve_inconsistencies(self, this_week, inconsistencies):
        """Removes excess courses and adds lacking courses to week.
        IN: (crossed) week object, inconsistencies dict with surplus and lacking
             both are list of courses
        OUT: (crossed) week object that represents all courses once"""
        full_list = this_week.list_time_slots()
        open_list = []

        for each_course in inconsistencies['surplus']:
            slots = this_week.find_course(each_course)
            for each_slot in slots:
                each_slot.remove_course()

        inconsistencies['lacking'].extend(inconsistencies['surplus'])

        # find all excess slots
        for i in full_list:
            if i.course is None:
                open_list.append(i)

        # fill in missing courses
        self.randomly_fill_schedule(
            this_week, inconsistencies['lacking'], open_list)

    ## combines weeks(schedules) P1 and P2 to create 2 child weeks then corrects if necessary
    #  @param self
    #  @param A Function that takes 2 parent schedules and produces a perfect schedule
    #  @return output
    def crossover(self, P1, P2):
        """Mixes weeks (schedules) P1 and P2 to create 2 children weeks, then corrects
        the children weeks as necessary
        IN: 2 parent schedules, P1 and P2
        OUT: 2 children schedules, C1 and C2, in a list"""
        output = []
        # the time slot(s) which will be moved between C1 and C2
        time_slots = []
        time_slot_indexes = []
        for i in range(self.slot_divide):
            index = randint(0, len(self.time_slots) - 1)
            if index not in time_slot_indexes:
                time_slots.append(self.time_slots[index])

        C1 = P1.deep_copy()
        C2 = P2.deep_copy()
        # P1's slots to have its courses cloned on P2
        cutA = self.find_time_slots_from_cuts(C1, time_slots)
        # P2's slots to have its courses cloned on P1
        cutB = self.find_time_slots_from_cuts(C2, time_slots)
        # do the replacement
        self.replace_time_slots(cutA, cutB)

        for i in [C1, C2]:
            # figure out what have extra of/don't have
            inconsistencies = self.assess_inconsistencies(i)
            # clear the excess; try to schedule lacking
            self.resolve_inconsistencies(i, inconsistencies)
            inconsistencies = self.assess_inconsistencies(i)
            #A week with extra courses is invalid, but not necessarily incomplete
            if len(inconsistencies["surplus"]) > 0:
                i.valid = False

            output.append(i)
        return output

    ## Produces a set of schedules based off the current set of schedules 
    #  @param self
    #  @param  A Function that creates more schedules based off the schedules that is passed in 
    #  @return none
    def breed(self):
        """Produces a set of schedules based off the current set of schedules"""
        def decide_prob_crossover(week1, week2, tilt = .1):
            valid_prob_crossover = (week1.valid + week2.valid) * .5
            if valid_prob_crossover == 0:
                valid_prob_crossover = .1

            if self.max_fitness == 0:
                return valid_prob_crossover

            total_fitness = (week1.fitness + week2.fitness) / 2.0
            fitness_prob_crossover = (total_fitness + (tilt *\
                     (self.max_fitness - total_fitness))) / self.max_fitness
            return valid_prob_crossover * fitness_prob_crossover

        if len(self.weeks) < 2:
            raise BreedError("Weeks is not the correct length")

        if not all(isinstance(each_week, Week) for \
                each_week in self.weeks):
            raise BreedError("An element in weeks is not a Week object")


        print("Max: ", max(i.fitness for i in self.weeks))
        list_of_children = []
        # combinations...(ex) 5 choose 2
        for each_week in range(len(self.weeks) - 1):
            for each_other_week in range(each_week + 1, len(self.weeks)):
                # decide if we are crossing over
                prob_crossover = decide_prob_crossover(self.weeks[each_week],
                                                       self.weeks[each_other_week])
                roll = randint(0, 100)
                if int(prob_crossover * 100) > roll:
                    children = self.crossover(self.weeks[each_week],
                                              self.weeks[each_other_week])
                    if len(children) > 0:
                        # Chance of mutation for each child
                        for each_child in children:
                            roll = randint(1, 3)
                            if roll == 2:
                                #self.mutate(each_child)
                                pass
                        # add to list of weeks
                    list_of_children.extend(children)
        self.weeks.extend(list_of_children)


    def loading_bar_update(self, one_increment, current_elapsed_seconds, max_runtime):
        """Increments the loading bar by as much as it should if and when it should"""
        #Currently, 40 is hard programmed into the GUI, so it is hard programmed here as well
        num_segments_displayed = self.loading_screen.load_bar['width']
        number_of_segments_to_add = (((current_elapsed_seconds * 1.0)/max_runtime) * 40.0) - num_segments_displayed
        while number_of_segments_to_add > 1:
            self.loading_screen.update_loading_bar()
            number_of_segments_to_add -= 1
        return


    ## Main loop that evolves and produces more schedules when run 
    #  @param self
    #  @param main tkinter window object
    #  @param number of minutes to run, int
    #  @return side-effect: self.weeks are filled out
    def evolution_loop(self, main_window_object, minutes_to_run = 1):
        """Main loop of scheduler, run to evolve towards a high fitness score"""
        start_time = now() #stopwatch starts

        # gui misc page object; for updating the loading bar
        self.loading_screen = main_window_object.misc_page

        main_window_object.setup_loading_screen()
        main_window_object.go_to_loading_screen()

        weeks_to_keep = 5

        if Counter(map(lambda x: x.name, self.constraints)) !=\
           Counter(map(lambda x: x.name, self.saved_state_of_constraints)):
               self.paused = False

        if self.paused:
            total_iterations = 11
            counter = 11
            time_limit = self.time_left_to_run - now()
        else:
            total_iterations = 0
            counter = 0
            time_limit = 60 * minutes_to_run
            
        one_increment = time_limit/40.0

        def week_slice_helper():
            """Sets self.weeks to the 5 best week options and returns the list of valid weeks"""
            valid_weeks = filter(lambda x: x.valid, self.weeks)
            valid_weeks.sort(key=lambda x: x.fitness, reverse=True)
            if len(valid_weeks) > 0:
                temp = filter(lambda x: not x.valid, self.weeks)[:weeks_to_keep \
                                                                    - len(valid_weeks)]
                temp.sort(key=lambda x: x.fitness, reverse=True)
                self.weeks = (valid_weeks + temp)[:weeks_to_keep]
            else:
                self.weeks = self.weeks[:weeks_to_keep]


            return valid_weeks

        if not self.paused:
            # Resetting self.weeks will trigger generate_starting_population() below
            self.weeks = []
        else:
            self.paused = False

        while True:
            print('Generation counter:', counter + 1)
            # self.gui_loading_info1 = 'Generation counter: ' + str(counter +1)

            self.weeks = filter(lambda x: x.complete, self.weeks)

            for each_week in self.weeks:
                each_week.update_sections(self.courses)
                self.calc_fitness(each_week)

            #Case that no schedules are complete or valid
            if len(self.weeks) == 0 or (len(filter(lambda x: x.valid, self.weeks)) == 0 and
                                        total_iterations < 9):
                # for case two only...reset before generate another 1000
                if len(self.weeks) >= 1000:
                    for i in range(len(self.weeks)):
                        del self.weeks[0]
                    gc.collect()

                self.generate_starting_population(1000, False, time_limit, 
                                                  start_time)
                total_iterations += 1
                counter += 1
                time_elapsed = now() - start_time
                self.loading_bar_update(one_increment, time_elapsed, time_limit)
                print("Time left for evolution loop: %d seconds" % (time_limit - time_elapsed))
                if time_elapsed > time_limit:
                    # need to assess the new weeks
                    for each_week in self.weeks:
                        each_week.update_sections(self.courses)
                        self.calc_fitness(each_week)
                    print('Time limit reached; final output found')
                    break
                continue

            valid_weeks = week_slice_helper()
            print("Calculated fitness")
            time_elapsed = now() - start_time
            self.loading_bar_update(one_increment, time_elapsed, time_limit)
            print("Time left for evolution loop: %d seconds" % (time_limit - time_elapsed))
            if time_elapsed > time_limit:
                print('Time limit reached; final output found')
                print('Min fitness of results is', str(min(i.fitness for i in self.weeks)))
                break

            print("Number of valid weeks for the generation:", str(len(valid_weeks)))

            if len(self.weeks) >= 5:
                top_5_min = min(i.fitness for i in self.weeks[0:5])
                top_5_avg = reduce(lambda x, y: x+y, [w.fitness for w in self.weeks[0:5]]) / 5
                print("Minimum fitness of the top schedules of the generation:", top_5_min)
                print("Average fitness of the top schedules of the generation:", top_5_avg)
                print("Max fitness for any schedule:", self.max_fitness)
                if top_5_min == top_5_avg and top_5_min != self.max_fitness:
                    print("Invoking guided mutatation")
                    
                    # decide a week and mutate it
                    choice = randint(0, 4)
                    self.guided_mutate(self.weeks[choice])
                    self.weeks[choice].update_sections(self.courses)
                    self.calc_fitness(self.weeks[choice])

                    # print out results
                    top_5_min = min(i.fitness for i in self.weeks[0:5])
                    top_5_avg = reduce(lambda x, y: x+y, [w.fitness for w in self.weeks[0:5]]) / 5
                    print("Minimum fitness of the top schedules after guided mutation:", top_5_min)
                    print("Average fitness of the top schedules after guided mutation:", top_5_avg)

            # self.gui_loading_info2 = "Minimum fitness of the top schedules of the generation: " + \
            #                          str(min(i.fitness for i in self.weeks))

            # self.gui_loading_info3 = "Number of valid weeks for the generation: " + \
            #                          str(len(valid_weeks))

            if len(self.weeks) >= 5:
                if min(i.fitness for i in self.weeks[0:5]) == self.max_fitness and \
                   len(valid_weeks) >= 5:
                    break

            # prepare for breed
            self.generate_starting_population(5)
            for each_week in self.weeks:
                each_week.update_sections(self.courses)
                self.calc_fitness(each_week)
            # breed
            print("Breed started with ", len(self.weeks), " weeks.")
            self.breed()
            print("Breed complete")

            total_iterations += 1
            counter += 1
            print("Number of weeks:", str(len(self.weeks)))
            print()
            if counter == 10 and len(valid_weeks) == 0:
                if main_window_object.ask_to_keep_running() == True:
                    self.paused = True
                    self.time_left_to_run = time_limit - time_elapsed 
                    self.saved_state_of_constraints = self.constraints[:]
                    
                    main_window_object.run_clicked = False 
                    main_window_object.go_to_constraints_screen()
                    break

        if not self.paused:
            print("Final number of generations: ", total_iterations + 1)
            main_window_object.finished_running()

    ## Provides all time slots matching in a given week
    #  @param self
    #  @param  A Function that finds all available time slots
    #  @return none
    def time_slot_available(self, day, first_time_slot):
        for room in day.rooms:
            if room.number != first_time_slot.room.number:
                continue

            for t_slot in room:
                if t_slot == first_time_slot and t_slot.course == None:
                    return (t_slot, True)

        return (None, False)

    ## Finds index of time slot object in list of time slots for week
    #  @param self
    #  @param  A time object that finds the index of time slots in a week
    #  @return none
    def find_index(self, time_slot, time_slot_list):
        """Finds index of time slot object in list of time slots for week"""
        counter = 0
        for each_slot in time_slot_list:
            if each_slot.room.number == time_slot.room.number and \
               each_slot.start_time == time_slot.start_time and \
               each_slot.end_time == each_slot.end_time and \
               each_slot.room.day.day_code == time_slot.room.day.day_code:
                return counter
            counter += 1
        print("Index not found")
        return


    ## Generates a dictionary describing the trends of the list of the time slots
    #  @param self
    #  @param  a dictionary object that list the time slot objects
    #  @return row_dict
    def assess_time_slot_row_for_open_slots(self, time_slots):
        """Generates a dictionary describing the trends of the list of time slots
        IN: list of time slot objects
        OUT: dictionary describing type of time slots, list of time slot objects,
             and open days
        Type: 0 for undefined, 1 for mwf, 2 for tr, 3 for both"""
        row_dict = {'days': '', 'time_slots': [], 'type': 0}
        for each_time_slot in time_slots:
            if each_time_slot.course is None:
                row_dict['time_slots'].append(each_time_slot)
                row_dict['days'] += each_time_slot.day

                if each_time_slot.isTR and row_dict['type'] == 0:
                    row_dict['type'] = 2
                elif not each_time_slot.isTR and row_dict['type'] == 0:
                    row_dict['type'] = 1
                elif (each_time_slot.isTR and row_dict['type'] == 1) or \
                     (not each_time_slot.isTR and row_dict['type'] == 2):
                    row_dict['type'] = 3
                elif (not each_time_slot.isTR and row_dict['type'] == 1) or \
                     (each_time_slot.isTR and row_dict['type'] == 2):
                    pass
                else:
                    print(each_time_slot.isTR)
                    print(row_dict['type'])
                    raise MalformedTimeslotError("Timeslot does not have a isTR attribute")

        return row_dict


    ## Assigns courses to the time slot and removes time slot from list of time slots
    #  @param self
    #  @param  a function that deletes time slot from list of time slots
    #  @return none
    def assign_and_remove(self, course, time_slot, slots_list, week):
        """Assigns course to time slot and removes time slot from list of time slots"""
        #i = self.find_index(time_slot, slots_list)
        schedule_slot = week.find_matching_time_slot(time_slot)
        i = self.find_index(schedule_slot, slots_list)
        schedule_slot.set_course(course)
        del(slots_list[i])


    ## Filters tr slots, mwf slots, prescheduled courses, and regular courses
    #  @param self
    #  @param  a function that returns time slot
    #  @return filtered_input
    def filter_for_generator(self, courses_list, list_of_slots_to_fill):
        """Filters tr slots, mwf slots, prescheduled courses, and regular courses"""
        filtered_input = {}
        prescheduled = filter(lambda x: x.is_prescheduled, courses_list)
        regular = filter(lambda x: not x.is_prescheduled, courses_list)
        filtered_input['prescheduled'] = prescheduled
        filtered_input['regular'] = regular
        return filtered_input

    ## Manually schedules a course at its designated time
    #  @param self
    #  @param  
    #  @return none
    def preschedule(self, week_to_fill, course):
        """Manually schedules a course at its designated time"""
        if not course.is_prescheduled:
            #log error
            return
        else:
            time_slots = week_to_fill.find_prescheduled_times(course)
            for each_time_slot in time_slots:
                if each_time_slot.course is not None:
                    #log error
                    pass
                each_time_slot.set_course(course)


    '''def schedule_5_hour_course(self, course, list_of_slots, this_week):
        """Randomly schedule a 5 hour course"""
        if course.credit != 5:
            raise FilterError("Schedule 5 hour course")

        random_slot = choice(mwf_slots)
        current_pool = deepcopy(mwf_slots)
        done = False
        while len(current_pool) > 0 and not done:
            possibilities = this_week.find_matching_time_slot_row(random_slot)
            possibilities = self.assess_time_slot_row_for_open_slots(possibilities)
            # each day open for that time and room
            if len(possibilities['time_slots']) == 5:
                for each_assignee in possibilities['time_slots']:
                    self.assign_and_remove(
                        course, each_assignee, list_of_time_slots, this_week)
                done = True
            # case that cannot schedule for this time and room
            else:
                # remove this timeslot and the other unoccupied in its
                # week from temp pool
                for to_remove in possibilities['time_slots']:
                    i = self.find_index(to_remove, current_pool)
                    del(current_pool[i])
                # get a new random time slot
                random_slot = choice(current_pool)
        #status
        return not done'''


    ## Randomly schedules 4 hour courses
    #  @param self
    #  @param  A function that generates 4 hour classes with list of time slots  
    #  @return not done
    def schedule_4_hour_course(self, course, list_of_time_slots, this_week):
        """Randomly schedule a 4 hour course"""
        if course.credit != 4:
            raise FilterError("Schedule 4 hour course")

        random_slot = choice(list_of_time_slots)
        current_pool = copy(list_of_time_slots)
        done = False
        while len(current_pool) > 0 and not done:
            possibilities = this_week.find_matching_time_slot_row(random_slot)
            possibilities = self.assess_time_slot_row_for_open_slots(possibilities)
            # each day open for that time and room
            if len(possibilities['time_slots']) == 5:
                #MWF
                for each_slot in possibilities['time_slots']:
                    if each_slot.day in 'mwf':
                        self.assign_and_remove(
                            course, each_slot, list_of_time_slots, this_week)
                #T or R
                j = randint(0, 1)
                if j:
                    for each_slot in possibilities['time_slots']:
                        if each_slot.day == 't':
                            self.assign_and_remove(
                                course, each_slot, list_of_time_slots, this_week)  # T
                else:
                    for each_slot in possibilities['time_slots']:
                        if each_slot.day == 'r':
                            self.assign_and_remove(
                                course, each_slot, list_of_time_slots, this_week)  # R
                done = True
            # case that mwf and either t or r are open
            elif all([x in possibilities['days'] for x in 'mwf']) and \
                    (all([x in possibilities['days'] for x in 't']) or \
                     all([x in possibilities['days'] for x in 'r'])):
                for each_slot in possibilities['time_slots']:
                    if each_slot.day in 'mwf':
                        self.assign_and_remove(
                            course, each_slot, list_of_time_slots, this_week)
                if all([x in possibilities['days'] for x in 't']):
                    for each_slot in possibilities['time_slots']:
                        if each_slot.day in 't':
                            self.assign_and_remove(
                                course, each_slot, list_of_time_slots, this_week)
                else:
                    for each_slot in possibilities['time_slots']:
                        if each_slot.day in 'r':
                            self.assign_and_remove(
                                course, each_slot, list_of_time_slots, this_week)
                done = True
            # case that cannot schedule for this time and room
            else:
                # remove this timeslot and the other unoccupied in its
                # week from temp pool
                for to_remove in possibilities['time_slots']:
                    i = self.find_index(to_remove, current_pool)
                    del(current_pool[i])
                # get a new random time slot
                random_slot = choice(current_pool)
        #status
        return not done


    ## Randomly schedules 3 hour courses
    #  @param self
    #  @param  A function that generates 3 hour classes with list of time slots  
    #  @return not done
    def schedule_3_hour_course(self, course, list_of_time_slots, this_week):
        """Randomly schedule a 3 hour course"""
        if course.credit != 3:
            raise FilterError("Schedule 3 hour course")

        random_slot = choice(list_of_time_slots)
        current_pool = copy(list_of_time_slots)
        done = False
        while len(current_pool) > 0 and not done:
            possibilities = this_week.find_matching_time_slot_row(random_slot)
            possibilities = self.assess_time_slot_row_for_open_slots(possibilities)
            # each day open for that time and room
            if len(possibilities['time_slots']) == 5:
                # MWF
                if not random_slot.isTR:
                    for each_slot in possibilities['time_slots']:
                        if each_slot.day in 'mwf':
                            self.assign_and_remove(
                                course, each_slot, list_of_time_slots, this_week)
                # TR
                else:
                    for each_slot in possibilities['time_slots']:
                        if each_slot.day in 'tr':
                            self.assign_and_remove(
                                course, each_slot, list_of_time_slots, this_week)
                done = True
            # case that mwf is open, but not tr
            elif all([x in possibilities['days'] for x in 'mwf']):
                for each_slot in possibilities['time_slots']:
                    if each_slot.day in 'mwf':
                        self.assign_and_remove(
                            course, each_slot, list_of_time_slots, this_week)
                done = True
            # case that tr is open, but not mwf
            elif all([x in possibilities['days'] for x in 'tr']) and possibilities['type'] == 2:
                for each_slot in possibilities['time_slots']:
                    if each_slot.day in 'tr':
                        self.assign_and_remove(
                            course, each_slot, list_of_time_slots, this_week)
                done = True
            # case that cannot schedule for this time and room
            else:
                # remove this timeslot and the other unoccupied in its
                # week from temp pool
                for to_remove in possibilities['time_slots']:
                    i = self.find_index(to_remove, current_pool)
                    del(current_pool[i])
                # get a new random time slot
                random_slot = choice(current_pool)
        #status
        return not done


    ## Randomly schedules 1 hour courses
    #  @param self
    #  @param  A function that generates 1 hour classes with list of time slots  
    #  @return not done
    def schedule_1_hour_course(self, course, list_of_slots, this_week):
        """Randomly schedule a 1 hour course"""
        if course.credit != 1:
            raise FilterError("Schedule 1 hour course")

        random_slot = choice(list_of_slots)
        current_pool = copy(list_of_slots)
        done = False
        while len(current_pool) > 0 and not done:
            possibilities = this_week.find_matching_time_slot_row(random_slot)
            possibilities = self.assess_time_slot_row_for_open_slots(possibilities)
            if course.is_lab: # tr
                # each day open for that time and room
                if possibilities['type'] == 2:
                    chosen = random.choice(possibilities['time_slots'])
                    self.assign_and_remove(
                            course, chosen, list_of_slots, this_week)
                    done = True

                # case that cannot schedule for this time and room
                else:
                    # remove this timeslot and the other unoccupied in its
                    # week from temp pool
                    for to_remove in possibilities['time_slots']:
                        i = self.find_index(to_remove, current_pool)
                        del(current_pool[i])
                    # get a new random time slot
                    random_slot = choice(current_pool)
            else: # mwf
                # each day open for that time and room
                if possibilities['type'] == 1:
                    chosen = random.choice(possibilities['time_slots'])
                    self.assign_and_remove(
                            course, chosen, list_of_slots, this_week)
                    done = True

                # case that cannot schedule for this time and room
                else:
                    # remove this timeslot and the other unoccupied in its
                    # week from temp pool
                    for to_remove in possibilities['time_slots']:
                        i = self.find_index(to_remove, current_pool)
                        del(current_pool[i])
                    # get a new random time slot
                    random_slot = choice(current_pool)
        #status
        return not done


    ## Randomly Fills in schedules 
    #  @param self
    #  @param  A function that generates random classes with list of slots time slots  
    #  @return none
    def randomly_fill_schedule(self, week_to_fill, courses_list, list_of_slots_to_fill):
        """Fills in random schedule for given week, courses, and time slots"""
        filtered = self.filter_for_generator(courses_list, list_of_slots_to_fill)
        prescheduled = filtered['prescheduled']
        regular = filtered['regular'] #regular courses...not prescheduled

        for each_course in prescheduled:
            try:
                self.manually_fill_schedule(week_to_fill, each_course)
            except: #specifically for error from above
                week_to_fill.valid = False
                week_to_fill.complete = False

        for each_course in regular:
            course_slots = filter(lambda x: x.course is None, list_of_slots_to_fill)

            if each_course.capacity > 70:
                course_slots = filter(lambda x: x.room.capacity > 70, course_slots)

            if each_course.needs_computers:
                course_slots = filter(lambda x: x.room.has_computers, course_slots)

            if len(course_slots) == 0:
                print('failure: incomplete schedule')
                week_to_fill.valid = False
                week_to_fill.complete = False
                return

            '''if each_course.credit == 5:
                failure = self.schedule_5_hour_course(each_course, course_slots, week_to_fill)'''
            if each_course.credit == 4:
                failure = self.schedule_4_hour_course(each_course, course_slots, week_to_fill)
            elif each_course.credit == 3:
                failure = self.schedule_3_hour_course(each_course, course_slots, week_to_fill)
            elif each_course.credit == 1:
                failure = self.schedule_1_hour_course(each_course, course_slots, week_to_fill)
            else:
                #error
                print("!!!Tried to schedule for an invalid number of credit hours!!!")
                week_to_fill.valid = False
                week_to_fill.complete = False
                return
            if failure:
                #cannot schedule in present situation
                print("failure: incomplete schedule")
                week_to_fill.valid = False
                week_to_fill.complete = False


    ## Randomly generates starting population
    #  @param self
    #  @param  A function that generates random population  
    #  @return not done
    def generate_starting_population(self, num_to_generate = 1000, just_one = False,
                                     time_limit = None, start_time = None):
        """Generates starting population"""
        #Quick case for getting to GUI
        if just_one and len(self.weeks) == 0:
            self.weeks.append(Week(self.rooms, self))
            one_week = self.weeks[0]
            list_slots = one_week.list_time_slots()
            self.randomly_fill_schedule(one_week, self.courses, list_slots)
            return None
        #Full generation
        old_number_of_schedules = len(self.weeks)
        for x in range(num_to_generate):
            self.weeks.append(Week(self.rooms, self))

        counter = 0
        if time_limit is not None:
            one_increment = time_limit/40.0
        for each_week in self.weeks[old_number_of_schedules:]:
            counter += 1
            list_slots = each_week.list_time_slots()
            self.randomly_fill_schedule(each_week, self.courses, list_slots)

            if counter % 50 == 0 and start_time is not None:
                current_elapsed_seconds = now() - start_time
                self.loading_bar_update(one_increment, current_elapsed_seconds, time_limit)

            #print("Schedule", counter, "generated")

            # update message to be shown on the gui loading screen
            # self.gui_loading_info = "Schedule " + str(counter) + " generated"

        if len(self.weeks) == 0:
            print("Could not schedule")
        print("Generated %d schedules" % num_to_generate)
        return None
