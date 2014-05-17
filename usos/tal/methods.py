from .factory.methods import (
    SimplePicker, ElementaryId, ElementaryIdList,
    LangDictPicker, DatePicker, EntityIdPicker, CompositeId, MappingPicker,
    USOSwebURLPicker, URLPicker, EntityIdListPicker, FieldPickers,
    Registry, AncestorFromListPicker, DecimalPicker, EntityIdMapPicker,
    CompositeTupleIdList, CoordsPicker, EntityFieldPickers, DateTimePicker)
from . import entities


registry = Registry()

primary_room_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    number=SimplePicker('number'),
    building=EntityFieldPickers(
        id=ElementaryId('building_id'),
        name=LangDictPicker('building_name'),
    ).make_inline_picker(),
    capacity=SimplePicker('capacity'),
)

secondary_room_field_pickers = FieldPickers()

primary_building_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    name=LangDictPicker('name'),
    location=CoordsPicker('location'),
)

path_faculty_field_pickers = EntityFieldPickers(  # allowed in 'path' field
    ElementaryId('id'),
    name=LangDictPicker('name'),
    profile_url=USOSwebURLPicker('profile_url'),
)

primary_faculty_field_pickers = path_faculty_field_pickers | FieldPickers(
    homepage_url=URLPicker('homepage_url'),
    parent=AncestorFromListPicker('path', path_faculty_field_pickers)
)

secondary_faculty_field_pickers = FieldPickers()

default_user_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    first_name=SimplePicker('first_name'),
    last_name=SimplePicker('last_name'),
)

primary_user_field_pickers = default_user_field_pickers | FieldPickers(
    sex=MappingPicker('sex', dict(M='male', F='female')),
    profile_url=USOSwebURLPicker('profile_url'),
    homepage_url=URLPicker('homepage_url'),
    phone_numbers=MappingPicker('phone_numbers', {None: []}, open=True),
    mobile_numbers=SimplePicker('mobile_numbers'),
    room=primary_room_field_pickers.make_picker('room'),
)

secondary_user_field_pickers = FieldPickers()

primary_course_group_field_pickers = EntityFieldPickers(
    CompositeId('course_unit_id', 'group_number'),
    course_unit=EntityFieldPickers(
        ElementaryId('course_unit_id'),
        course_edition=EntityFieldPickers(
            CompositeId('course_id', 'term_id'),
            course=EntityFieldPickers(
                ElementaryId('course_id'),
                name=LangDictPicker('course_name'),
            ).make_inline_picker(),
            term=EntityIdPicker('term_id'),
        ).make_inline_picker(),
        class_type=EntityFieldPickers(
            ElementaryId('class_type_id'),
            name=LangDictPicker('class_type'),
        ).make_inline_picker(),
    ).make_inline_picker(),
    group_number=SimplePicker('group_number'),
    lecturers=default_user_field_pickers.make_list_picker('lecturers', has_subfield_selector=False),
    participants=default_user_field_pickers.make_list_picker('participants', has_subfield_selector=False),
    homepage_url=URLPicker('group_url'),
)

secondary_course_group_field_pickers = FieldPickers(
    description=LangDictPicker('group_description'),
    literature=LangDictPicker('group_literature'),
)

primary_thesis_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    type=SimplePicker('type'),
    name=LangDictPicker('titles'),
    authors=primary_user_field_pickers.make_list_picker('authors'),
    supervisors=primary_user_field_pickers.make_list_picker('supervisors'),
    faculty=primary_faculty_field_pickers.make_picker('faculty'),
)

primary_programme_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    name=LangDictPicker('description'),
    mode_of_studies=LangDictPicker('mode_of_studies'),
    level_of_studies=LangDictPicker('level_of_studies'),
    duration=LangDictPicker('duration'),
    professional_status=LangDictPicker('professional_status'),
)

registry.register_get_method(
    path='services/progs/programme',
    entity_class=entities.Programme,
    id=ElementaryId('programme_id'),
    field_pickers=primary_programme_field_pickers,
)

registry.register_get_many_method(
    path='services/progs/programmes',
    entity_class=entities.Programme,
    ids=ElementaryIdList('programme_ids'),
    field_pickers=primary_programme_field_pickers,
)


registry.register_get_method(
    path='services/users/user',
    entity_class=entities.User,
    id=ElementaryId('user_id'),
    field_pickers=primary_user_field_pickers | secondary_user_field_pickers
)

registry.register_get_many_method(
    path='services/users/users',
    entity_class=entities.User,
    ids=ElementaryIdList('user_ids'),
    field_pickers=primary_user_field_pickers,
    limit=30,
)

registry.register_get_method(
    path='services/fac/faculty',
    entity_class=entities.Faculty,
    id=ElementaryId('fac_id'),
    field_pickers=primary_faculty_field_pickers | secondary_faculty_field_pickers,
)

registry.register_get_many_method(
    path='services/fac/faculties',
    entity_class=entities.Faculty,
    ids=ElementaryIdList('fac_ids'),
    field_pickers=primary_faculty_field_pickers,
    limit=100,
)

primary_term_fields = FieldPickers(
    order_key=SimplePicker('order_key'),
    name=LangDictPicker('name'),
    start_date=DatePicker('start_date'),
    end_date=DatePicker('end_date'),
)

registry.register_get_method(
    path='services/terms/term',
    entity_class=entities.Term,
    id=ElementaryId('term_id'),
    field_pickers=primary_term_fields,
    has_fields_param=False
)

registry.register_get_many_method(
    path='services/terms/terms',
    entity_class=entities.Term,
    ids=ElementaryIdList('term_ids'),
    field_pickers=primary_term_fields,
    has_fields_param=False
)

primary_course_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    name=LangDictPicker('name'),
    profile_url=USOSwebURLPicker('profile_url'),
    homepage_url=URLPicker('homepage_url'),
    currently_conducted=SimplePicker('is_currently_conducted'),
    faculty=EntityIdPicker('fac_id'),
)

secondary_course_field_pickers = FieldPickers(
    description=LangDictPicker('description'),
    bibliography=LangDictPicker('bibliography'),
    learning_outcomes=LangDictPicker('learning_outcomes'),
    assessment_criteria=LangDictPicker('assessment_criteria'),
    practical_placement=LangDictPicker('practical_placement'),
)

registry.register_get_method(
    path='services/courses/course',
    entity_class=entities.Course,
    id=ElementaryId('course_id'),
    field_pickers=primary_course_field_pickers | secondary_course_field_pickers
)

registry.register_get_many_method(
    path='services/courses/courses',
    entity_class=entities.Course,
    ids=ElementaryIdList('course_ids'),
    field_pickers=primary_course_field_pickers
)

crstests_course_edition_field_pickers = EntityFieldPickers(
    CompositeId('course_id', 'term_id'),
    course=EntityFieldPickers(
        ElementaryId('course_id'),
        name=LangDictPicker('course_name'),
    ).make_inline_picker(),
    term=EntityIdPicker('term_id'),
    profile_url=USOSwebURLPicker('profile_url'),
    homepage_url=URLPicker('homepage_url'),
)

primary_course_edition_field_pickers = crstests_course_edition_field_pickers | FieldPickers(
    coordinators=default_user_field_pickers.make_list_picker('coordinators', has_subfield_selector=False),
    lecturers=default_user_field_pickers.make_list_picker('lecturers', has_subfield_selector=False, unique=True),
)

secondary_course_edition_field_pickers = FieldPickers(
    participants=default_user_field_pickers.make_list_picker('participants', has_subfield_selector=False),
    description=LangDictPicker('description'),
    bibliography=LangDictPicker('bibliography'),
    notes=LangDictPicker('notes'),
    course_units=EntityIdListPicker('course_units_ids')
)

registry.register_get_method(
    path='services/courses/course_edition',
    entity_class=entities.CourseEdition,
    id=CompositeId('course_id', 'term_id'),
    field_pickers=primary_course_edition_field_pickers | secondary_course_edition_field_pickers
)

# registry.register_get_method(
#     path='services/grades/course_edition',
#     entity_class=entities.CourseEdition,
#     id=CompositeId('course_id', 'term_id'),
#     field_pickers=FieldPickers(
#         grades=EntityFieldPickers(
#             CompositeId('grade_type_id', 'value_symbol'),
#             symbol=SimplePicker('value_symbol'),
#             name=LangDictPicker('value_description'),
#             grade_type=EntityIdPicker('grade_type_id'),
#         ).make_map_picker('course_grades'),
#     ),
#     has_fields_param=False,
#     extra_params=dict(
#         fields='grade_type_id|value_symbol|value_description',
#     ),
# )

primary_course_unit_field_pickers = FieldPickers(
    profile_url=USOSwebURLPicker('profile_url'),
    homepage_url=URLPicker('homepage_url'),
    class_type=EntityIdPicker('classtype_id'),
    course_edition=EntityFieldPickers(
        CompositeId('course_id', 'term_id'),
        course=EntityFieldPickers(
            ElementaryId('course_id'),
            name=LangDictPicker('course_name'),
        ).make_inline_picker(),
        term=EntityIdPicker('term_id'),
    ).make_inline_picker(),
)

secondary_course_unit_field_pickers = FieldPickers(
    learning_outcomes=LangDictPicker('learning_outcomes'),
    assessment_criteria=LangDictPicker('assessment_criteria'),
    topics=LangDictPicker('topics'),
    teaching_methods=LangDictPicker('teaching_methods'),
    bibliography=LangDictPicker('bibliography'),
    groups=primary_course_group_field_pickers.make_list_picker('groups'),
)

registry.register_get_method(
    path='services/courses/unit',
    entity_class=entities.CourseUnit,
    id=ElementaryId('unit_id'),
    field_pickers=primary_course_unit_field_pickers | secondary_course_unit_field_pickers,
)

registry.register_get_many_method(
    path='services/courses/units',
    entity_class=entities.CourseUnit,
    ids=ElementaryIdList('unit_ids'),
    field_pickers=primary_course_unit_field_pickers,
)

registry.register_get_many_method(
    path='services/courses/classtypes_index',
    entity_class=entities.ClassType,
    ids=ElementaryIdList('_'),
    field_pickers=FieldPickers(
        name=LangDictPicker('name'),
    ),
)

registry.register_get_method(
    path='services/groups/group',
    entity_class=entities.CourseGroup,
    id=CompositeId('course_unit_id', 'group_number'),
    field_pickers=primary_course_group_field_pickers | secondary_course_group_field_pickers,
)

registry.register_get_many_method(
    path='services/groups/groups',
    entity_class=entities.CourseGroup,
    ids=CompositeTupleIdList('group_ids'),
    field_pickers=primary_course_group_field_pickers,
)

registry.register_get_method(
    path='services/geo/room',
    entity_class=entities.Room,
    id=ElementaryId('room_id'),
    field_pickers=primary_room_field_pickers | secondary_room_field_pickers,
)

registry.register_get_many_method(
    path='services/geo/rooms',
    entity_class=entities.Room,
    ids=ElementaryIdList('room_ids'),
    field_pickers=primary_room_field_pickers,
)

registry.register_get_method(
    path='services/geo/building2',
    entity_class=entities.Building,
    id=ElementaryId('building_id'),
    field_pickers=primary_building_field_pickers,
)

registry.register_get_many_method(
    path='services/geo/buildings2',
    entity_class=entities.Building,
    ids=ElementaryIdList('building_ids'),
    field_pickers=primary_building_field_pickers,
)

registry.register_get_method(
    path='services/theses/thesis',
    entity_class=entities.Thesis,
    id=ElementaryId('ths_id'),
    field_pickers=primary_thesis_field_pickers,
)

registry.register_get_many_method(
    path='services/theses/theses',
    entity_class=entities.Thesis,
    ids=ElementaryIdList('ths_ids'),
    field_pickers=primary_thesis_field_pickers,
)

registry.register_get_method(
    path='services/theses/user',
    entity_class=entities.User,
    id=ElementaryId('user_id'),
    field_pickers=FieldPickers(
        authored_theses=primary_thesis_field_pickers.make_list_picker('authored_theses'),
    ),
)

registry.register_get_many_method(
    path='services/theses/users',
    entity_class=entities.User,
    ids=ElementaryIdList('user_ids'),
    field_pickers=FieldPickers(
        authored_theses=primary_thesis_field_pickers.make_list_picker('authored_theses'),
    ),
)

registry.register_search_method(
    path='services/users/search2',
    entity_class=entities.User,
    picker=primary_user_field_pickers.make_picker('user'),
)

registry.register_search_method(
    path='services/theses/search',
    entity_class=entities.Thesis,
    picker=primary_thesis_field_pickers.make_picker('thesis'),
)

registry.register_search_method(
    path='services/fac/search',
    entity_class=entities.Faculty,
    picker=primary_faculty_field_pickers.make_inline_picker(),
    fields_param_mode='partial',
)

registry.register_search_method(
    path='services/courses/search',
    entity_class=entities.Course,
    picker=EntityIdPicker('course_id'),
    fields_param_mode='none',
    query_param_name='name',
)

for domain, active_only in (('student', 'true'), ('student_all', 'false')):
    registry.register_list_method(
        domain=domain,
        path='services/groups/participant',
        entity_class=entities.CourseGroup,
        entity_field_pickers=primary_course_group_field_pickers,
        list_selector=('groups', '*', '*'),
        extra_params=dict(active_terms=active_only)
    )

for domain, active_only in (('user', 'true'), ('user_all', 'false')):
    registry.register_list_method(
        domain=domain,
        path='services/courses/user',
        entity_class=entities.CourseEdition,
        entity_field_pickers=primary_course_edition_field_pickers,
        extra_params=dict(active_terms_only=active_only),
        list_selector=('course_editions', '*', '*'),
        x_fields_wrapper='course_editions[{0}]',
    )

for domain, active_only in (('student', 'true'), ('student_all', 'false')):
    registry.register_list_method(
        domain=domain,
        path='services/progs/student',
        entity_class=entities.Programme,
        entity_field_pickers=primary_programme_field_pickers,
        extra_params=dict(active_only=active_only),
        list_selector=('*', 'programme'),
        x_fields_wrapper='programme[{0}]',
    )

grade_field_pickers = EntityFieldPickers(
    CompositeId('grade_type_id', 'symbol'),
    symbol=SimplePicker('symbol'),
    name=LangDictPicker('name'),
    passes=SimplePicker('passes'),
    decimal_value=DecimalPicker('decimal_value'),
    order_key=SimplePicker('order_key'),
    grade_type=EntityIdPicker('grade_type_id'),
)

primary_course_test_root_node_field_pickers = EntityFieldPickers(
    ElementaryId('node_id'),
    name=LangDictPicker('name'),
    type=MappingPicker('type', dict(
        root='root',
        fld='folder',
        folder='folder',
        pkt='task',
        task='task',
        oc='grade',
        grade='grade'
    )),
    order_key=SimplePicker('order'),
    description=SimplePicker('description'),
    course_edition=crstests_course_edition_field_pickers.make_picker('course_edition', has_subfield_selector=False),
    parent=EntityIdPicker('parent_id'),
)

primary_course_test_node_field_pickers = primary_course_test_root_node_field_pickers | FieldPickers(
    min_points=SimplePicker('points_min'),
    max_points=SimplePicker('points_max'),
    precision=SimplePicker('points_precision'),
    grade_type=EntityFieldPickers(ElementaryId('id')).make_picker('grade_type', has_subfield_selector=False),
)

secondary_course_test_node_field_pickers = FieldPickers(
    algorithm=EntityFieldPickers(
        ElementaryId('node_id'),
        dependencies=EntityIdMapPicker('dependencies', flipped=True),
        variables=SimplePicker('variables'),
        source=SimplePicker('algorithm'),
        description=SimplePicker('description'),
    ).make_inline_picker()
)

registry.register_get_method(
    path='services/crstests/node',
    entity_class=entities.CourseTestNode,
    id=ElementaryId('node_id'),
    field_pickers=primary_course_test_node_field_pickers | secondary_course_test_node_field_pickers,
    extra_params=dict(
        recursive='false',
    ),
)

registry.register_get_many_as_list_method(
    path='services/crstests/user_points',
    entity_class=entities.CourseTestNode,
    ids=ElementaryIdList('node_ids'),
    entity_field_pickers=EntityFieldPickers(
        ElementaryId('node_id'),
        test_points=EntityFieldPickers(
            ElementaryId('node_id'),
            points=SimplePicker('points'),
            comment=SimplePicker('comment'),
            last_modified=DateTimePicker('last_changed'),
            grader=EntityIdPicker('grader_id'),
        ).make_inline_picker()
    ),
    has_fields_param=False,
)

registry.register_get_many_as_list_method(
    path='services/crstests/user_grades',
    entity_class=entities.CourseTestNode,
    ids=ElementaryIdList('node_ids'),
    entity_field_pickers=EntityFieldPickers(
        ElementaryId('node_id'),
        test_grade=EntityFieldPickers(
            ElementaryId('node_id'),
            # FIXME this terrible hack will cause severe damage when someone tries to access grade identifier
            grade=(EntityFieldPickers(ElementaryId('symbol')) | grade_field_pickers).make_picker('grade'),
            comment=SimplePicker('private_comment'),
            last_modified=DateTimePicker('last_changed'),
            grader=EntityIdPicker('grader_id'),
        ).make_inline_picker()
    ),
    has_fields_param=False,
)

# This case is too complex to compute proper 'fields' parameter value
registry.register_get_method(
    path='services/crstests/node',
    entity_class=entities.CourseTestNode,
    id=ElementaryId('node_id'),
    field_pickers=primary_course_test_node_field_pickers | FieldPickers(
        subnodes=primary_course_test_node_field_pickers.make_list_picker('subnodes')
    ),
    has_fields_param=False,
    extra_params=dict(
        recursive='true',
        fields='node_id|parent_id|order|name|type|course_edition|description|points_min|points_max|points_precision|'
               'grade_type|subnodes',
    ),
)

registry.register_list_method(
    domain='student_all',
    path='services/crstests/participant',
    entity_class=entities.CourseTestNode,
    entity_field_pickers=primary_course_test_root_node_field_pickers,
    list_selector=('tests', '*', '*'),
    has_fields_param=False
)

primary_grade_type_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    name=LangDictPicker('name'),
    values=grade_field_pickers.make_list_picker(
        'values',
        has_subfield_selector=False,
        lifted_fields={'id': 'grade_type_id'}
    )
)

registry.register_get_method(
    path='services/grades/grade_type',
    entity_class=entities.GradeType,
    id=ElementaryId('grade_type_id'),
    field_pickers=primary_grade_type_field_pickers,
)

primary_exam_grade_field_pickers = EntityFieldPickers(
    CompositeId('exam_id', 'exam_session_number'),
    grade=EntityFieldPickers(
        CompositeId('grade_type_id', 'value_symbol'),
        symbol=SimplePicker('value_symbol'),
        name=LangDictPicker('value_description'),
        grade_type=EntityIdPicker('grade_type_id'),
    ).make_inline_picker(),
    exam_session=EntityIdPicker('exam_id', 'exam_session_number'),
    comment=SimplePicker('comment'),
    modified_date=DateTimePicker('date_modified'),
    modified_by=default_user_field_pickers.make_picker('modification_author', has_subfield_selector=False),
)

secondary_exam_grade_field_pickers = FieldPickers(
    course_edition=primary_course_edition_field_pickers.make_picker('course_edition'),
)

primary_exam_session_field_pickers = EntityFieldPickers(
    CompositeId('exam_id', 'number'),
    number=SimplePicker('number'),
    status=SimplePicker('status'),
    name=LangDictPicker('description'),
    deadline=DateTimePicker('deadline'),
)

registry.register_get_method(
    path='services/examrep/exam_session',
    entity_class=entities.ExamSession,
    id=CompositeId('exam_id', 'number'),
    field_pickers=primary_exam_session_field_pickers,
)

registry.register_get_method(
    path='services/grades/grade',
    entity_class=entities.ExamGrade,
    id=CompositeId('exam_id', 'exam_session_number'),
    field_pickers=primary_exam_grade_field_pickers | secondary_exam_grade_field_pickers,
)

registry.register_get_method(
    path='services/grades/exam',
    entity_class=entities.Exam,
    id=ElementaryId('exam_id'),
    field_pickers=FieldPickers(
        exam_grades=primary_exam_grade_field_pickers.make_inline_list_picker()
    )
)

primary_exam_field_pickers = EntityFieldPickers(
    ElementaryId('id'),
    name=LangDictPicker('description'),
    editable=SimplePicker('is_editable'),
    # FIXME bug in USOSapi
    # grade_type=primary_grade_type_field_pickers.make_picker('grade_type'),
)

secondary_exam_field_pickers = FieldPickers(
    sessions=primary_exam_session_field_pickers.make_list_picker('sessions', lifted_fields=dict(id='exam_id')),
    course_edition=EntityFieldPickers(
        CompositeId('id', 'term_id'),
        term=EntityIdPicker('term_id'),
        course=primary_course_field_pickers.make_inline_picker(),
    ).make_picker('course', lifted_fields=dict(term_id='term_id')),
)

registry.register_get_method(
    path='services/examrep/exam',
    entity_class=entities.Exam,
    id=ElementaryId('id'),
    field_pickers=primary_exam_field_pickers | secondary_exam_field_pickers,
)

registry.register_list_method(
    domain='user',
    path='services/cards/user',
    entity_class=entities.Card,
    entity_field_pickers=EntityFieldPickers(
        ElementaryId('barcode_number'),
        barcode_number=SimplePicker('barcode_number'),
        contact_chip_uid=SimplePicker('contact_chip_uid'),
        contactless_chip_uid=SimplePicker('contactless_chip_uid'),
        type=SimplePicker('type'),
        expiration_date=DatePicker('expiration_date'),
    ),
    list_selector=('*', ),
    has_fields_param=False
)

# TODO add also getter method
installation_field_pickers = EntityFieldPickers(
    ElementaryId('base_url'),
    name=LangDictPicker('institution_name'),
    base_url=SimplePicker('base_url'),
    version=SimplePicker('version'),
    contact_emails=SimplePicker('contact_emails'),
)

registry.register_list_method(
    domain='public',
    path='services/apisrv/installations',
    entity_class=entities.Installation,
    entity_field_pickers=installation_field_pickers,
    list_selector=('*', ),
    has_fields_param=False
)