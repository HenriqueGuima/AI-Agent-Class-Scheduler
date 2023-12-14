import random
from ortools.sat.python import cp_model

# GLOBAL VARIABLES
global_variable_classes = ["ClassA", "ClassB", "ClassC"]
global_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]


def create_model():
    return cp_model.CpModel()


def randomize_lists():
    # DECLARE VARIABLES
    # UC = SUBJECT
    ClassA = "UC11 UC12 UC13 UC14 UC15".split()
    ClassB = "UC21 UC22 UC23 UC24 UC25".split()
    ClassC = "UC31 UC32 UC33 UC34 UC35".split()

    Prof1 = "UC31 UC22 UC13 UC24 UC15".split()
    Prof2 = "UC21 UC12 UC23 UC34 UC25".split()
    Prof3 = "UC11 UC32 UC33 UC14 UC35".split()

    rooms = "Room_C Room_N Room_T".split()

    # RANDOMIZE ORDER IN THE LISTS
    random.shuffle(ClassA)
    random.shuffle(ClassB)
    random.shuffle(ClassC)
    random.shuffle(Prof1)
    random.shuffle(Prof2)
    random.shuffle(Prof3)
    random.shuffle(rooms)

    return ClassA, ClassB, ClassC, Prof1, Prof2, Prof3, rooms


def create_bool_var(model, name):
    return model.NewBoolVar(name)


# DOMAIN FUNCTION
def create_decision_variables(model, classes, rooms):
    return {
        (subject, t, r): create_bool_var(model, f"class_{subject}_{t}_{r}")
        for subject in classes
        for t in range(1, 21)
        for r in rooms
    }


# ASSIGNS CLASSES TO DAYS
def create_days_of_classes(model, classes):
    return {
        (_class, day): create_bool_var(model, f"class_day_{_class}_{day}")
        for _class in classes
        for day in range(5)
    }


# ASSIGNS CLASSROOMS TO EACH TIME PERIOD AND CHECKS IF THE SUM OF THE LESSONS TO EACH SUBJECT IS LESS OR EQUAL TO 1
def add_classroom_constraints(model, lessons, classes, rooms):
    for r in rooms:
        for t in range(1, 18):
            model.Add(sum(lessons[(subject, t, r)] for subject in classes) <= 1)


# ASSIGNS EACH CLASS TO A TIME PERIOD AND CHECKS IF THE SUM OF THE THE LESSONS TO EACH CLASS IN EACH TIME PERIOD ACROSS ALL ROOMS IF IT'S LESS OR EQUAL TO 1
def add_single_class_per_timeslot_constraints(
    model, lessons, classes, rooms, class_sub
):
    for _class in global_variable_classes:
        for timetable in range(1, 18):
            model.Add(
                sum(
                    lessons[(subject, timetable, r)]
                    # FILTERS SUBJECTS BASED ON THE CLASS THEY BELONG TO
                    for subject in classes
                    if class_sub[subject] == _class
                    for r in rooms
                )
                <= 1
            )


# CHECKS THE TOTAL NUMBER OF LESSONS FOR EACH TIME PERIOD AND ROOMS
def add_weekly_lessons_constraints(
    model, lessons, classes, rooms, class_sub, minlessons, maxlessons
):
    for _class in global_variable_classes:
        lessons_class_sum = sum(
            lessons[(subject, t, r)]
            for subject in classes
            if class_sub[subject]
            == _class  # GETS THE SUBJECTS BASED ON THE CLASSES THEY BELONG
            for t in range(1, 18)
            for r in rooms
        )
        model.Add(
            minlessons <= lessons_class_sum
        )  # CONSTRAINT TO MAKE SURE THE NUMBER OF LESSONS IS GREATER OR EQUAL TO THE MINUMUM, WHICH WOULD BE 4
        model.Add(
            lessons_class_sum <= maxlessons
        )  # CONSTRAINT TO MAKE SURE THE NUMBER OF LESSONS IS LESS OR EQUAL TO THE THE MAXIMUM, WHICH WOULD BE 10


# ADDS A CONSTRAINT FOR THE NUMBER OF LESSONS IN A DAY
def add_daily_lessons_constraints(
    model, lessons, classes, rooms, class_sub, max_lessons_per_day
):
    for _class in global_variable_classes:
        for day in range(5):
            # CALCULATE THE START AND ENDING OF THE DAY THAT WOULD HAVE 4 TIME PERIODS FOR EACH DAY

            start = day * 4 + 1
            end = (day + 1) * 4

            # SUMS ALL COMBINATIONS OF SUBJECTS, TIME PERIODS AND ROOMS FOR A SPECIFIC CLASS AND DAY
            model.Add(
                sum(
                    lessons[(subject, t, r)]  # AND RETRIEVES THEM
                    for subject in classes
                    if class_sub[subject] == _class  # FILTER
                    for t in range(start, end + 1)
                    for r in rooms
                )
                <= max_lessons_per_day  # CONSTRAINT THAT MAKES SURE THE SUMS OF THE LESSONS ARE LESS OR EQUAL TO THE VARIABLE MAX_LESSONS_PER_DAY WHICH WOULD BE 3
            )


# CONSTRAINT TO MAKE SURE THE NUMBER OF CLASSES ARE NOT MORE THAN 4 IN EACH DAY
def add_max_days_with_classes_constraint(
    model, days_of_classes, classes, max_classes_in_a_day
):
    for _class in global_variable_classes:
        days_sum = sum(
            model.NewBoolVar(f"{_class}_{day}") for day in range(5)
        )  # CHECKS IF THERE IS AT LEAST ONE CLASS ON A SPECIFIC DAY
        model.Add(
            days_sum <= max_classes_in_a_day
        )  # ENSURES THAT THE TOTAL NUMBER OF DAYS WITH CLASSES IS LESS OR EQUAL TO THE SPECIFIED LIMIT (4)


# CONSTRAINT TO ENSURE THAT THE MINUMUM OF LESSONS PER SUBJECT IS LESS OR EQUAL TO THE SPECIFIED LIMIT (2)
def add_min_lessons_per_uc_constraint(
    model, lessons, classes, rooms, min_lessons_per_subject
):
    for subject in classes:
        model.Add(
            sum(
                lessons[(subject, t, r)] for t in range(1, 18) for r in rooms
            )  # TOTAL NUMBER OF LESSONS PER CURRENT SUBJECT
            >= min_lessons_per_subject
        )


def create_objective_function(model, lessons, classes, rooms):
    # IN THIS CASE WE ARE PRIORITIZING THE MORNING TIME PERIODS TO ASSIGN THE LESSONS

    # MORNING LESSONS ARE BETWEEN 1 AND 5 (ASSUMING IT WOULD BE 9H TO 13H)
    morning = sum(
        lessons[(subject, timetable, room)] * (4 - timetable)  # MORNING WEIGHT
        for subject in classes
        for timetable in range(1, 5)  # MORNING LESSONS
        for room in rooms
    )

    # AFTERNOON LESSONS ARE BETWEEN 6 AND 10 (ASSUMING IT WOULD BE 13H TO 17H)
    afternoon = sum(
        lessons[(subject, timetable, room)] * (10 - timetable)  # AFTERNOONG WEIGHT
        for subject in classes
        for timetable in range(6, 10)  # AFTERNOON LESSONS
        for room in rooms
    )

    objective_expression = morning + afternoon
    return objective_expression


# PRINT
def print_schedule(solver, lessons, class_sub, professors_sub, rooms, classes):
    for timetable in range(9, 18):  # 9H TO 18H DAYS
        for room in rooms:
            timetable_lessons = [
                subject
                for subject in classes
                if solver.Value(lessons[(subject, timetable, room)])
            ]

            # CHECK IF LESSONS EXIST
            if timetable_lessons:
                for subject in timetable_lessons:
                    # TUPLE UNPACKING. CHECKS IF THE KEY IS THE SAME IN BOTH CLASS_SUB AND PROFESSORS_SUB DICTIONARIES
                    _class, professor = class_sub[subject], professors_sub[subject]

                    print(
                        (f"{_class} | {subject} | {professor} | {room}"),
                        (f"at {timetable}h"),
                    )

            # UNCOMMENT TO PRINT EMPTY TIME PERIODS
            # else:
            #     print(f"{_class} |      |       | {room} at {timetable}h")


def print_schedule_for_class(
    solver, lessons, class_sub, professors_sub, rooms, classes, target_class
):
    for day in range(5):
        print(f"\n\n--- {global_days[day]} ---")
        for timetable in range(9, 18):
            for room in rooms:
                timetable_lessons = [
                    subject
                    for subject in classes
                    if solver.Value(lessons.get((subject, timetable, room), 0))
                    and class_sub[subject] == target_class
                ]
                if timetable_lessons:
                    for subject in timetable_lessons:
                        professor = professors_sub[subject]
                        print(
                            (f"{target_class} | {subject} | {professor} | {room}"),
                            (f"at {timetable}h"),
                        )


def print_statistics(solver, lessons, rooms, classes):
    lessons_per_sub = [
        sum(solver.Value(lessons[(subject, t, r)]) for t in range(1, 18) for r in rooms)
        for subject in classes
    ]
    # print(lessons_per_sub)


def main():
    # CREATE MODEL
    model = create_model()

    for day in range(5):
        print(f"\n\n--- {global_days[day]} ---")

        # SET VARIABLES
        ClassA, ClassB, ClassC, Prof1, Prof2, Prof3, rooms = randomize_lists()
        classes = ClassA + ClassB + ClassC

        # print("ClassA:", ClassA)
        # print("ClassB:", ClassB)
        # print("ClassC:", ClassC)
        # print("Prof1:", Prof1)
        # print("Prof2:", Prof2)
        # print("Prof3:", Prof3)
        # print("Salas:", rooms)

        class_sub = {subject: "ClassA" for subject in ClassA}
        # ADD THE REST OF THE MAPPINGS
        class_sub.update({subject: "ClassB" for subject in ClassB})
        class_sub.update({subject: "ClassC" for subject in ClassC})
        professors_sub = {subject: "Prof1" for subject in Prof1}
        professors_sub.update({subject: "Prof2" for subject in Prof2})
        professors_sub.update({subject: "Prof3" for subject in Prof3})

        # DOMAIN
        lessons = create_decision_variables(model, classes, rooms)
        days_of_classes = create_days_of_classes(model, classes)

        # CONSTRAINTS
        add_classroom_constraints(model, lessons, classes, rooms)
        add_single_class_per_timeslot_constraints(model, lessons, classes, rooms, class_sub)
        add_weekly_lessons_constraints(
            model, lessons, classes, rooms, class_sub, 4, 10
        )  # WEEKLY LESSONS SHOULD BE BETWEEN 4 AND 10
        add_daily_lessons_constraints(
            model, lessons, classes, rooms, class_sub, 3
        )  # DAILY LESSONS SHOULDN'T BE MORE THAN 3
        add_max_days_with_classes_constraint(
            model, days_of_classes, classes, 4
        )  # MAXIMUM CLASSES PER DAY SHOULD BE LESS OR EQUAL TO 4
        add_min_lessons_per_uc_constraint(
            model, lessons, classes, rooms, 2
        )  # MINIMUM LESSONS PER SUBJECT ARE 2

        # GOAL
        objective_function = create_objective_function(model, lessons, classes, rooms)
        model.Maximize(objective_function)

        solver = cp_model.CpSolver()
        solver.parameters.search_branching = cp_model.AUTOMATIC_SEARCH

        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print_schedule(solver, lessons, class_sub, professors_sub, rooms, classes)
            # UNCOMMENT TO PRINT ONLY ONE CLASS
            # print_schedule_for_class(solver, lessons, class_sub, professors_sub, rooms, classes,  target_class="ClassA")

        else:
            print("NO SOLUTION")

        # print_statistics(solver, lessons, rooms, classes)


if __name__ == "__main__":
    main()
