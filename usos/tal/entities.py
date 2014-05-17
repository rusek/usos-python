from .factory.entities import (
    Entity, DataField, EntityField, EntityListField, OptionalEntityField, EntityMapField,
    StringType, ListType, OptionalType, EnumType, URLType, PhoneNumberType, DateType,
    BoolType, DecimalType, IntType, CoordsType, OpenEnumType, DateTimeType, EmailType
)

# TODO crstests: groups, user_grades, user_points
# TODO grades: course edition / course unit grades
# TODO photos
# TODO plctests
# TODO tt
# TODO examrep: course edition exams
# TODO StudentProgramme?
# TODO apiref
# TODO apisrv: consumer


class Installation(Entity):
    name = DataField(StringType, default=True)
    base_url = DataField(URLType)
    version = DataField(StringType)
    contact_emails = DataField(ListType(EmailType))


class Card(Entity):
    barcode_number = DataField(StringType, default=True)
    contact_chip_uid = DataField(StringType)
    contactless_chip_uid = DataField(StringType)
    type = DataField(EnumType('student', 'phd', 'staff'))
    expiration_date = DataField(DateType)
    # TODO missing get function


class Building(Entity):
    name = DataField(StringType, default=True)
    location = DataField(OptionalType(CoordsType))


class Programme(Entity):
    name = DataField(StringType, default=True)
    mode_of_studies = DataField(StringType)
    level_of_studies = DataField(StringType)
    duration = DataField(StringType)  # TODO rename to duration_description?
    professional_status = DataField(StringType)


class Room(Entity):
    number = DataField(StringType, default=True)
    building = EntityField(Building, default=True)
    capacity = DataField(OptionalType(IntType))
    # TODO type


class User(Entity):
    entity_searchable = True

    first_name = DataField(StringType, default=True)
    last_name = DataField(StringType, default=True)
    sex = DataField(EnumType('male', 'female'))
    # email - available only for access token issuer, not so useful for the time being
    profile_url = DataField(URLType)
    homepage_url = DataField(OptionalType(URLType))
    phone_numbers = DataField(ListType(PhoneNumberType))
    mobile_numbers = DataField(ListType(PhoneNumberType))
    room = OptionalEntityField(Room)
    authored_theses = EntityListField('Thesis')
    # TODO has_photo, photo_urls, student_number
    # pesel is really sensitive data - better don't allow to fetch it at all
    # TODO student_programmes, employment_functions, emplyment_positions


class Grade(Entity):
    symbol = DataField(StringType, default=True)
    name = DataField(StringType, default=True)
    grade_type = EntityField('GradeType')
    passes = DataField(BoolType)
    decimal_value = DataField(DecimalType)
    order_key = DataField(IntType)


class GradeType(Entity):
    name = DataField(StringType, default=True)
    values = EntityListField(Grade)


class Exam(Entity):
    name = DataField(StringType, default=True)
    exam_grades = EntityListField('ExamGrade')
    sessions = EntityListField('ExamSession')
    course_edition = EntityField('CourseEdition')
    editable = DataField(BoolType)
    grade_type = EntityField(GradeType)
    # TODO type


class ExamSession(Entity):
    name = DataField(StringType, default=True)
    number = DataField(IntType)
    status = DataField(StringType)  # or enum?
    deadline = DataField(DateTimeType)
    # TODO editable


class ExamGrade(Entity):
    # FIXME there is no user_id in ID (maybe that's ok?)
    grade = EntityField(Grade, default=True)
    exam_session = EntityField(ExamSession)
    comment = DataField(StringType)
    course_edition = EntityField('CourseEdition')
    modified_date = DataField(DateTimeType)
    modified_by = EntityField(User)
    # TODO counts_into_average, course_unit, user
    # TODO exam subfields may be extracted using grades/grade


class Term(Entity):
    name = DataField(StringType, default=True)
    order_key = DataField(IntType)
    start_date = DataField(DateType)
    end_date = DataField(DateType)


class Faculty(Entity):
    entity_searchable = True

    name = DataField(StringType, default=True)
    profile_url = DataField(URLType)
    homepage_url = DataField(OptionalType(URLType))
    parent = OptionalEntityField('Faculty')
    # TODO phone_numbers, postal_address, stats, static_map_urls, logo_urls
    # TODO what about subfaculties?


class Thesis(Entity):
    entity_searchable = True

    name = DataField(StringType, default=True)
    type = DataField(OpenEnumType('doctoral', 'master', 'licentiate', 'engineer'))
    authors = EntityListField(User)
    supervisors = EntityListField(User)
    faculty = EntityField(Faculty)


class Course(Entity):
    entity_searchable = True

    name = DataField(StringType, default=True)
    profile_url = DataField(URLType)
    homepage_url = DataField(OptionalType(URLType))
    currently_conducted = DataField(BoolType)
    faculty = EntityField(Faculty)
    description = DataField(StringType)
    bibliography = DataField(StringType)
    learning_outcomes = DataField(StringType)
    assessment_criteria = DataField(StringType)
    practical_placement = DataField(StringType)
    # TODO lang_id


class CourseTestAlgorithm(Entity):
    # FIXME variant=True is a hack - currently each node contains an algorithm
    dependencies = EntityMapField('CourseTestNode', variant=True)
    variables = DataField(StringType, variant=True)
    source = DataField(StringType, variant=True)
    description = DataField(StringType, variant=True)


class CourseTestPoints(Entity):
    # FIXME should ID include user_id?
    points = DataField(OptionalType(DecimalType), default=True)
    comment = DataField(StringType)
    last_modified = DataField(OptionalType(DateTimeType))
    grader = EntityField(User)


class CourseTestGrade(Entity):
    # FIXME should ID include user_id?
    grade = EntityField(Grade)
    comment = DataField(StringType)
    last_modified = DataField(OptionalType(DateTimeType))
    grader = EntityField(User)


class CourseTestNode(Entity):
    name = DataField(StringType, default=True)
    # TODO root
    subnodes = EntityListField('CourseTestNode')
    type = DataField(EnumType('root', 'folder', 'task', 'grade'))
    order_key = DataField(IntType)
    parent = OptionalEntityField('CourseTestNode')

    # root nodes
    description = DataField(StringType, variant=True)
    course_edition = OptionalEntityField('CourseEdition', variant=True)

    # task nodes
    min_points = DataField(DecimalType, variant=True)  # float? decimal?
    max_points = DataField(DecimalType, variant=True)  # float? decimal?
    precision = DataField(IntType, variant=True)
    test_points = OptionalEntityField(CourseTestPoints, variant=True)

    # grade nodes
    grade_type = OptionalEntityField(GradeType, variant=True)
    test_grade = OptionalEntityField(CourseTestGrade, variant=True)

    algorithm = OptionalEntityField(CourseTestAlgorithm, variant=True)

    # TODO limit_to_groups, my_permissions, permissions, visible_for_students


class CourseEdition(Entity):
    course = EntityField(Course, default=True)
    term = EntityField(Term, default=True)
    profile_url = DataField(URLType)
    homepage_url = DataField(OptionalType(URLType))
    coordinators = EntityListField(User)
    lecturers = EntityListField(User)
    participants = EntityListField(User)
    description = DataField(StringType)
    bibliography = DataField(StringType)
    notes = DataField(StringType)
    course_units = EntityListField('CourseUnit')
    # grades = EntityMapField(Grade)  # TODO what about nulls? course unit grades?


class ClassType(Entity):
    name = DataField(StringType, default=True)


class CourseUnit(Entity):
    course_edition = EntityField(CourseEdition, default=True)
    class_type = EntityField(ClassType, default=True)
    profile_url = DataField(URLType)
    homepage_url = DataField(OptionalType(URLType))
    learning_outcomes = DataField(StringType)
    assessment_criteria = DataField(StringType)
    topics = DataField(StringType)
    teaching_methods = DataField(StringType)
    bibliography = DataField(StringType)
    groups = EntityListField('CourseGroup')


class CourseGroup(Entity):
    course_unit = EntityField(CourseUnit, default=True)
    group_number = DataField(IntType, default=True)  # TODO string? what about group "2b" (theoretically...)
    homepage_url = DataField(URLType)  # TODO what about profile_url?
    lecturers = EntityListField(User)
    participants = EntityListField(User)
    description = DataField(StringType)
    literature = DataField(StringType)
