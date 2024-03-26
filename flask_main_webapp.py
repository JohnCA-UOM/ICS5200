import asyncio
import random
import string

import nest_asyncio
import requests
from flask import Flask, request, render_template, jsonify, make_response, redirect, url_for, session, abort

from common import *
from session_data import SessionData

session_items_dictionary = {}

students_to_numbers = {
    'jeremy_student': 0,
    'lily_student': 1,
    'emma_student': 2,
    'max_student': 3,
    'lisa_student': 4,
    'josh_student': 5,
    'teacher': 10
}
numbers_to_students = {
    '0': 'jeremy_student',
    '1': 'lily_student',
    '2': 'emma_student',
    '3': 'max_student',
    '4': 'lisa_student',
    '5': 'josh_student'
}

app = Flask(__name__)
#app.secret_key = os.urandom(24)
app.secret_key = '94wFx5I110fHwTksadwabbvbbfxhjt'

""" Gets Country Code based on IP """
def get_country_code_from_ip(ip):
    # Build URL used to get information on IP
    url = f"http://ip-api.com/json/{ip}"

    # Get Geolocation Information from IP using above URL
    response = requests.get(url, headers={"pragma": "no-cache"})

    # If Successful, return Country Code, else Print what went wrong
    if response.json()["status"] == "success":
        return response.json()["countryCode"]
    else:
        print(response.json())


""" Root Route, Used to redirect user to saved state based on data saved in session """
@app.route("/")
def index():
    global session_items_dictionary

    # If country_code or logged_in are not in session, then send to login pag e
    if 'country_code' not in session or 'logged_in' not in session:
        return redirect(url_for('login'))

    # If country_code is not MT, then don't allow
    if session['country_code'] != 'MT':
        print('NOT FROM MALTA')
        abort(403)

    # If not logged into session, then send to Login Page
    if not session['logged_in']:
        return redirect(url_for('login'))

    if 'username' in session:
        # If username not in session_items_dictionary, then remove username from session
        if session['username'] not in session_items_dictionary:
            session.pop('username')

            return redirect(url_for('phase_select_page'))

        # If username in session_items_dictionary, and user was in menu, send to Main Menu
        elif session_items_dictionary[session['username']].in_menu:
            return redirect(url_for('detail_entry_for_class_simulation'))

        # If username in session_items_dictionary, and user was in lesson, send to Class Simulation Page
        elif session_items_dictionary[session['username']].in_lesson:

            return redirect(url_for('class_simulation'))

    # If username not in session, send to Phase Selector Page
    else:
        return redirect(url_for('phase_select_page'))


""" Log In Route, First page accessible by the user before accessing the Experiment """
@app.route("/login")
def login():
    # If country_code doesn't exist, then get it from ip
    if 'country_code' not in session:
        # Clear Session due to Missing Country Code
        session.clear()

        # Get Remote Address of the User accessing the Website
        user_ip = request.remote_addr

        # Save IP in Session for future use
        session['ip_address'] = user_ip

        # If local, automatically assign MT
        if user_ip == '127.0.0.1':
            session['country_code'] = 'MT'

        # Else, go through process of getting Country Code
        else:
            # Get Country Code using IP and Save it to Session
            session['country_code'] = get_country_code_from_ip(user_ip)

            # If not from Malta, don't allow Access
            if session['country_code'] != 'MT':
                print('NOT FROM MALTA')
                abort(403)
            else:
                print('FROM MALTA, ALLOW!')

    # Else If not from Malta, don't allow Access
    elif session['country_code'] != 'MT':
        abort(403)

    # If Already Logged In, then go to Phase Select Page
    if 'logged_in' in session:
        if session['logged_in']:
            return redirect(url_for('phase_select_page'))

    # If none of the above conditions are met, then show User Login Page
    return render_template('login.html')

""" Check whether Password entered by User is Correct """
@app.route("/check_login_pass", methods=['POST'])
def check_login_pass():

    # If country_code doesn't exist, then sent to Root URL
    if 'country_code' not in session:
        print('NO COUNTRY CODE OR LOGGED IN')
        return redirect(url_for('index'))

    # Else If not from Malta, don't allow Access
    elif session['country_code'] != 'MT':
        abort(403)

    if request.method == 'POST':
        json_obj = request.json

        # Get Password submitted by User
        password = json_obj['password']

        # Load saved Password
        hashed_pass = load_from_pickle('./resources/passwords/login_pass.pickle')

        # Compare User inputted Password with saved Password
        pass_result = checkPassword(password, hashed_pass)

        if pass_result['valid']:
            # If Returned a Valid Response but not a Correct Password, Return an Error Response
            if not pass_result['correct_pass']:
                return make_response(jsonify({'ok': False, 'message': 'Incorrect Password, Try Again.'}), 401)
            # If Returned a Valid Response and a Correct Password, Set logged_in to True
            else:
                session['logged_in'] = True

                # Send User to Phase Selector Page
                return redirect(url_for('phase_select_page'))
        else:
            # If didn't Return a Valid Response, Return an Error Response
            return make_response(jsonify({'ok': False, 'message': 'Only Accepts Strings, Try Again.'}), 401)


""" Phase Selector Page Route, Accessible after Logging In. Allows User to choose Experiment Phase """
@app.route('/phaseselectpage')
def phase_select_page():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    # If in_lesson_phase and in_review_phase both don't exist, then default them to False.
    if 'in_lesson_phase' not in session and 'in_review_phase' not in session:
        session['in_lesson_phase'] = False

        session['in_review_phase'] = False

    # Else, If in_lesson_phase, send to Lesson Menu, Else if in_review_phase, send to Review Menu
    else:
        if session['in_lesson_phase']:
            return redirect(url_for('detail_entry_for_class_simulation'))
        elif session['in_review_phase']:
            return redirect(url_for('get_lesson_for_review'))

    # Render Page for Experiment Phase Selector
    return render_template('phase_select_page.html')


""" Check which Phase was selected, routes to correct page """
@app.route('/choose_phase/<phase_name>', methods=['GET'])
def choose_phase(phase_name):
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'GET':
        # If phase name is lesson, then send to Deliver Lesson Phase
        if phase_name == 'lesson':
            session['in_lesson_phase'] = True

            return redirect(url_for('detail_entry_for_class_simulation'))

        # If phase name is review, then send to Review Lesson Phase
        elif phase_name == 'review':
            session['in_review_phase'] = True

            return redirect(url_for('get_lesson_for_review'))


""" Go back to Phase Selector Page from either Experiment Phase Menu"""
@app.route('/go_back', methods=['POST'])
def go_back():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    # If in_lesson_phase and in_review_phase do not exist, redirect back to Phase Selector Page
    if 'in_lesson_phase' not in session and 'in_review_phase' not in session:
        return redirect(url_for('phase_select_page'))

    # Set in_review_phase and in_lesson_phase to False
    session['in_review_phase'] = False
    session['in_lesson_phase'] = False

    # Route back to Phase Selector Page
    return redirect(url_for('phase_select_page'))


""" Detail Entry for Class Simulation Route, Allows entry of Details, get Unique ID and Start Class Simulation """
@app.route("/detailentryforclasssimulation")
def detail_entry_for_class_simulation():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    global session_items_dictionary

    teacher_gender = ""

    if 'in_lesson_phase' in session and 'in_review_phase' in session:
        # If in Lesson Phase then continue to Display Page
        if session['in_lesson_phase']:

            if 'username' in session:
                username = session['username']

                if session['username'] in session_items_dictionary:
                    # If username already exists in session_items_dictionary and user is in lesson, then route to Class Simulation Page
                    if session_items_dictionary[username].in_lesson:
                        return redirect(url_for('class_simulation'))

            # If username doesn't exist, then generate a unique one
            else:
                chars = string.ascii_lowercase + string.digits

                # Keep on Generating ID until Unique One Found
                while True:
                    unique_id = True

                    memorable_id = ''.join(random.choice(chars) for _ in range(10))

                    check_path_or_create('logger/')

                    for i in os.listdir('logger/'):
                        if i == memorable_id:
                            unique_id = False
                            break

                    if unique_id:
                        break

                # Save Unique ID to Session
                session['username'] = memorable_id

            # Render Page to allow User to Enter Details and Start Class Simulation
            return render_template('detail_entry_for_class_simulation.html',
                                   teacher_id=session['username'],
                                   teacher_gender=teacher_gender)

        # If in Review Phase then route to Review Phase PAge
        elif session['in_review_phase']:
            return redirect(url_for('get_lesson_for_review'))

        # If in neither phase, route to Phase Selector Page
        else:
            return redirect(url_for('phase_select_page'))

    # If in_lesson_phase and in_review_phase don't exist, route back to Root URL
    else:
        return redirect(url_for('index'))


""" Start Class Simulation Route, goes through the process of starting the Class Simulation """
@app.route("/start_class_sim", methods=['POST'])
def start_class_sim():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    global session_items_dictionary

    if request.method == 'POST':
        json_obj = request.json

        # Get Gender and year passed from Front-End
        teacher_gender = json_obj['teacher_gender']
        student_year = json_obj['student_year']
        login_timestamp = round(time.time(), 3)

        username = session['username']

        session['login_time'] = login_timestamp

        # Set Gender in Session
        session['gender'] = teacher_gender

        # Set Student Year in Session
        session['student_year'] = student_year

        ip_address = session['ip_address']

        if len(session_items_dictionary) > 4:
            return make_response(jsonify({'ok': False, 'message': f'Too many teachers are delivering lessons, try again in 30 minutes.'}), 401)

        session_items_dictionary[username] = SessionData(username, teacher_gender, student_year, ip_address, login_timestamp)

        session_items_dictionary[username].in_menu = False
        session_items_dictionary[username].in_lesson = True

        session_items_dictionary[username].current_student_value = -1

        session_items_dictionary[username].print_data()

        check_path_or_create(f'logger/{username}')

        session_items_dictionary[username].save_session_to_file(username)

        return redirect(url_for('class_simulation'))


@app.route("/classsimulation")
def class_simulation():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    global session_items_dictionary

    if 'username' in session:
        username = session['username']

        if username not in session_items_dictionary:
            session.pop('username')

            return redirect(url_for('detail_entry_for_class_simulation'))
    else:
        return redirect(url_for('index'))

    in_menu = session_items_dictionary[username].in_menu
    in_lesson = session_items_dictionary[username].in_lesson

    sim = session_items_dictionary[username].simulation

    current_student_value = session_items_dictionary[username].current_student_value
    current_student_talking_to = session_items_dictionary[username].current_student_talking_to
    current_action_chosen = session_items_dictionary[username].current_action_chosen

    portion_of_chat_history = []

    if in_lesson and not in_menu:
        if len(sim.general_chat_history) > 20:
            for i in range(len(sim.general_chat_history) - 20, len(sim.general_chat_history)):
                for chat_log in sim.general_chat_history[i]:
                    portion_of_chat_history.append(chat_log.to_obj())
        else:
            for i in range(0, len(sim.general_chat_history)):
                for chat_log in sim.general_chat_history[i]:
                    portion_of_chat_history.append(chat_log.to_obj())

        agent_emoticons = sim.agent_emoticons

        fin_returned_data = []

        for i in portion_of_chat_history:
            dict_item = i

            if dict_item['guid'] == 'teacher':
                dict_item['student_num'] = 10
            else:
                dict_item['student_num'] = list(sim.agents).index(
                        dict_item['guid'])

            fin_returned_data.append(dict_item)

        if current_student_value == -1 or current_student_value > len(list(sim.agents)) - 1:
            return render_template('class_simulation.html',
                                   chat_history=fin_returned_data,
                                   agent_emoticons=agent_emoticons,
                                   current_student_value=current_student_value,
                                   current_student_talking_to=current_student_talking_to,
                                   current_action_chosen=current_action_chosen,
                                   current_button_selected=-1,
                                   name='Student Name',
                                   teacher_gender=session_items_dictionary[username].teacher_gender)
        else:
            curr_selected_student = sim.agents[list(sim.agents)[current_student_value]]

            return render_template('class_simulation.html',
                                   chat_history=fin_returned_data,
                                   agent_emoticons=agent_emoticons,
                                   current_student_value=current_student_value,
                                   current_student_talking_to=current_student_talking_to,
                                   current_action_chosen=current_action_chosen,
                                   current_button_selected=current_student_value,
                                   name=curr_selected_student.persona.name,
                                   gender=curr_selected_student.persona.gender,
                                   age=curr_selected_student.persona.age,
                                   enjoyment=curr_selected_student.persona.enjoyment,
                                   anger=curr_selected_student.persona.anger,
                                   boredom=curr_selected_student.persona.boredom,
                                   anxiety=curr_selected_student.persona.anxiety,
                                   creativity=curr_selected_student.persona.creative,
                                   curiosity=curr_selected_student.persona.curious,
                                   tolerance=curr_selected_student.persona.tolerant,
                                   persistence=curr_selected_student.persona.persistent,
                                   responsibility=curr_selected_student.persona.responsible,
                                   selfcontrol=curr_selected_student.persona.self_control,
                                   teacher_gender=session_items_dictionary[username].teacher_gender)


@app.route('/talk_to_class', methods=['POST'])
async def talk_to_class():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    global session_items_dictionary

    username = session['username']

    if request.method == 'POST':
        json_obj = request.json

        user_input = json_obj['user_input']
        session_items_dictionary[username].current_student_talking_to = talking_to_chosen = json_obj['talking_to_choice']
        session_items_dictionary[username].current_action_chosen = action_chosen = json_obj['action_choice']

        input_start_time = round(time.time(), 3)

        recent_chat_history = []

        if len(session_items_dictionary[username].simulation.general_chat_history) > 5:
            for i in range(len(session_items_dictionary[username].simulation.general_chat_history) - 5,
                           len(session_items_dictionary[username].simulation.general_chat_history)):
                for chat_log in session_items_dictionary[username].simulation.general_chat_history[i]:
                    recent_chat_history.append(chat_log)
        else:
            for i in range(0, len(session_items_dictionary[username].simulation.general_chat_history)):
                for chat_log in session_items_dictionary[username].simulation.general_chat_history[i]:
                    recent_chat_history.append(chat_log)

        game_breaker_resp, question_suitability_resp, chat_analysis_resp = await asyncio.gather(
            run_prompt_and_convert_to_obj('game_breaker_prompt.yaml',
                                          print_prompt=True,
                                          user_input=user_input,
                                          chat_history=recent_chat_history,
                                          class_year=session_items_dictionary[username].simulation.class_year),
            run_prompt_and_convert_to_obj('question_suitability_prompt.yaml',
                                          print_prompt=False,
                                          user_input=user_input,
                                          chat_history=recent_chat_history,
                                          student_age=session_items_dictionary[username].simulation.student_age),
            run_prompt_and_convert_to_obj('chat_analysis_prompt.yaml',
                                          print_prompt=False,
                                          user_input=user_input,
                                          chat_history=recent_chat_history)
        )

        for i in [game_breaker_resp, question_suitability_resp, chat_analysis_resp]:
            if not i['valid']:
                return make_response(jsonify({'ok': False, 'message': i['response'], 'resp_data': None}), 400)

        initial_models_end_time = round(time.time(), 3)

        game_breaker_resp = game_breaker_resp['response']
        question_suitability_resp = question_suitability_resp['response']
        chat_analysis_resp = chat_analysis_resp['response']

        chat_analysis_resp['talking_to'] = talking_to_chosen
        chat_analysis_resp['action_chosen'] = action_chosen

        print('------------------------------- Initial Models Response -------------------------------')
        print("Initial Models Time Taken:", round(initial_models_end_time - input_start_time, 3))
        print('Game Breaker: ', game_breaker_resp)
        print('Question Suitability: ', question_suitability_resp)
        print('Chat Analysis: ', chat_analysis_resp)
        print('------------------------------- Initial Models Response -------------------------------')

        if game_breaker_resp['allowed']:

            returned_data = await session_items_dictionary[username].simulation.tick(user_input, input_start_time, chat_analysis_resp, question_suitability_resp)

            tick_end_time = round(time.time(), 3)

            if not returned_data['valid']:
                return make_response(jsonify({'ok': False, 'message': returned_data['response'], 'resp_data': None}), 400)

            returned_data = returned_data['response']

            print('initial Models End: ', round(initial_models_end_time - input_start_time, 3))
            print('Tick End: ', round(tick_end_time - input_start_time, 3))

            fin_returned_data = []

            for i in returned_data:
                dict_item = i

                dict_item['student_num'] = list(session_items_dictionary[username].simulation.agents).index(dict_item['agent_guid'])

                fin_returned_data.append(dict_item)

            agent_emoticons = session_items_dictionary[username].simulation.agent_emoticons

            teacher_id = session_items_dictionary[username].teacher_id

            await session_items_dictionary[username].simulation.save_data(teacher_id)

            return make_response(jsonify({'ok': True, 'message': 'Successful', 'resp_data': {'new_text': returned_data, 'new_agent_emoticons': agent_emoticons}}), 200)
        else:
            return make_response(jsonify({'ok': False, 'message': f'Input not Allowed: {game_breaker_resp["reason"]}'}), 400)


@app.route('/get_student_details/<int:student_number>', methods=['GET'])
def get_student_details(student_number):
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    global session_items_dictionary

    username = session['username']

    agents = session_items_dictionary[username].simulation.agents

    if request.method == 'GET':

        if student_number == session_items_dictionary[username].current_student_value:
            session_items_dictionary[username].current_student_value = -1

            return jsonify({'response': 'student unchosen'})

        session_items_dictionary[username].current_student_value = student_number

        if student_number > (len(agents)-1):
            return jsonify({"message": "Error", "dataNumber": 'no student found'})

        curr_selected_student = agents[list(agents)[student_number]]

        return jsonify(curr_selected_student.persona.to_obj())


@app.route("/end_lesson", methods=['POST'])
async def end_lesson():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    global session_items_dictionary

    if request.method == 'POST':

        username = session['username']

        teacher_id = session_items_dictionary[username].teacher_id

        save_time = round(time.time(), 3)

        session_items_dictionary[username].in_menu = True
        session_items_dictionary[username].in_lesson = False
        session_items_dictionary[username].finished_lesson = True

        """ Save Simulation Data and Delete Everything. """

        await session_items_dictionary[username].simulation.save_data(teacher_id)

        session_items_dictionary[username].delete_collection()

        session_items_dictionary[username].init_chromadb_collection()

        session_items_dictionary[username].init_simulation()

        """ Save Simulation Data and Delete Everything. """

        """ Save to file and Delete Teacher Session Details """
        session_items_dictionary[username].logout_time = save_time

        session_items_dictionary[username].save_session_to_file(teacher_id)

        if username in session_items_dictionary:
            session_items_dictionary.pop(username)

        logged_in = session['logged_in']
        country_code = session['country_code']
        ip_address = session['ip_address']

        session.clear()

        session['logged_in'] = logged_in
        session['country_code'] = country_code
        session['ip_address'] = ip_address
        """ Save to file and Delete Teacher Session Details """

        return redirect(url_for('phase_select_page'))


@app.route("/getlessonforreview")
async def get_lesson_for_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if 'in_lesson_phase' in session and 'in_review_phase' in session:
        if session['in_review_phase']:

            if 'in_review' in session:
                if session['in_review']:
                    return redirect(url_for('lesson_review'))

            folder_path = f'logger'

            general_list_of_lessons = []
            list_of_lessons_for_review = []

            for i in os.listdir(folder_path):
                curr_path = f'{folder_path}/{i}/session_details.pickle'

                session_data = load_from_pickle(curr_path)

                general_list_of_lessons.append(session_data['teacher_id'])

                if session_data['finished_lesson'] and not session_data['finished_review'] and not session_data['currently_being_reviewed']:
                    list_of_lessons_for_review.append(session_data['teacher_id'])

            session['general_list_of_lessons'] = general_list_of_lessons
            session['list_of_lessons_for_review'] = list_of_lessons_for_review

            return render_template('get_lesson_for_review_menu.html')
        elif session['in_lesson_phase']:
            return redirect(url_for('detail_entry_for_class_simulation'))
        else:
            return redirect(url_for('phase_select_page'))


@app.route("/start_lesson_review", methods=['POST'])
async def start_lesson_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'POST':
        json_obj = request.json

        id_inputted = json_obj['teacher_id']
        #student_year = json_obj['student_year']

        list_of_lessons_for_review = session['list_of_lessons_for_review']

        if id_inputted in session['general_list_of_lessons']:
            if id_inputted in session['list_of_lessons_for_review']:
                list_of_lessons_for_review.remove(id_inputted)
        else:
            return make_response(jsonify({'ok': False, 'message': 'ID does not Exist, Try Again.'}), 401)

        # Removed filter by Year because only using Year 5 / 6
        '''list_of_lessons_after_class_filter = []

        for i in session['list_of_lessons_for_review']:

            session_data_for_review = load_from_pickle(f'logger/{i}/session_details.pickle')

            if session_data_for_review['student_year'] == student_year:
                list_of_lessons_after_class_filter.append(i)

        list_of_lessons_for_review = list_of_lessons_after_class_filter'''

        while True:
            if len(list_of_lessons_for_review) == 0:
                return make_response(jsonify({'ok': False, 'message': 'No Lessons Left to Review.'}), 401)

            chosen_id = random.choice(list_of_lessons_for_review)

            print('CHOSEN ID: ', chosen_id)

            session['teacher_id'] = id_inputted

            curr_path = f'logger/{chosen_id}'

            session['lesson_folder_path'] = curr_path

            session_data_for_review = load_from_pickle(f'{curr_path}/session_details.pickle')

            if session_data_for_review['currently_being_reviewed']:
                list_of_lessons_for_review.remove(chosen_id)

                print('Chosen Lesson already being reviewed')
            else:
                session['lesson_name'] = chosen_id

                session_data_for_review['currently_being_reviewed'] = True

                session_data_for_review['reviewed_by'] = session['teacher_id']

                dump_to_pickle(f'{curr_path}/session_details.pickle', session_data_for_review)

                break

        session['student_folder_paths'] = []

        session['past_tick_data'] = {}

        session['persona_details'] = {}

        session['review_tick'] = -1
        session['curr_selected_student'] = -1
        session['action_taken'] = -1
        session['in_review'] = True

        return redirect(url_for("lesson_review"))


@app.route("/lessonreview")
async def lesson_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if 'in_lesson_phase' in session and 'in_review_phase' in session:
        if session['in_review_phase']:

            if 'lesson_name' not in session:
                return redirect(url_for('get_lesson_for_review'))
            if 'writing_review' in session:
                if session['writing_review']:
                    return redirect(url_for('write_review'))

            session_data = load_from_pickle(f'{session["lesson_folder_path"]}/session_details.pickle')

            student_past_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_past_data.pickle')
            student_final_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_final_data.pickle')

            session['persona_details'] = student_final_data

            if session['review_tick'] == -1:
                filtered_tick_data = student_past_data[0]
            else:
                filtered_tick_data = student_past_data[session['review_tick']]

            session['past_tick_data_chosen'] = filtered_tick_data

            new_chat_history = load_from_pickle(f'{session["lesson_folder_path"]}/general_chat_history.pickle')

            start_tick = max(0, session['review_tick'] - 15 + 1)

            filtered_chat_history = []

            for i in range(start_tick, session['review_tick'] + 1):
                for j in new_chat_history[i]:
                    filtered_chat_history.append(j)

            talking_to = 'default'
            action_chosen = 'default'
            agent_emoticons = [None, None, None, None, None, None]

            if len(filtered_chat_history) != 0:
                element_with_max_tick = max(filtered_chat_history, key=lambda x: x['tick'])

                talking_to = element_with_max_tick['chat_analysis_resp']['talking_to']
                action_chosen = element_with_max_tick['chat_analysis_resp']['action_chosen']
                agent_emoticons = element_with_max_tick['agent_emoticons']

            fin_returned_data = []

            for dict_item in filtered_chat_history:
                dict_item['student_num'] = students_to_numbers[dict_item['guid']]

                fin_returned_data.append(dict_item)

            if session['curr_selected_student'] == -1:
                return render_template('lesson_review.html',
                                       current_student_value=session['curr_selected_student'],
                                       max_tick_value=len(student_past_data),
                                       chat_history=fin_returned_data,
                                       teacher_gender=session_data['teacher_gender'],
                                       agent_emoticons=agent_emoticons,
                                       name='Student Name',
                                       current_student_talking_to=talking_to,
                                       current_action_chosen=action_chosen,
                                       curr_tick=session['review_tick'] + 1)
            else:

                student_id = numbers_to_students[str(session['curr_selected_student'])]

                persona_data = session['persona_details'][student_id]['persona']

                if session['review_tick'] == len(student_past_data):
                    emotions = {
                        'enjoyment': persona_data['enjoyment'],
                        'boredom': persona_data['boredom'],
                        'anger': persona_data['anger'],
                        'anxiety': persona_data['anxiety']
                    }
                else:
                    if session['review_tick'] == -1:
                        emotions = session['past_tick_data_chosen'][student_id]['emotions_original']
                    else:
                        emotions = session['past_tick_data_chosen'][student_id]['emotions_updated']

                return render_template('lesson_review.html',
                                       current_student_value=session['curr_selected_student'],
                                       max_tick_value=len(student_past_data),
                                       chat_history=fin_returned_data,
                                       teacher_gender=session_data['teacher_gender'],
                                       agent_emoticons=agent_emoticons,
                                       current_student_talking_to=talking_to,
                                       current_action_chosen=action_chosen,
                                       name=persona_data['name'],
                                       age=persona_data['age'],
                                       gender=persona_data['gender'],
                                       curr_tick=session['review_tick'] + 1,
                                       enjoyment=emotions['enjoyment'],
                                       anger=emotions['anger'],
                                       boredom=emotions['boredom'],
                                       anxiety=emotions['anxiety'],
                                       creativity=persona_data['creative'],
                                       curiosity=persona_data['curious'],
                                       tolerance=persona_data['tolerant'],
                                       persistence=persona_data['persistent'],
                                       responsibility=persona_data['responsible'],
                                       selfcontrol=persona_data['self_control'])
        elif session['in_lesson_phase']:
            return redirect(url_for('detail_entry_for_class_simulation'))
        else:
            return redirect(url_for('phase_select_page'))


@app.route('/change_tick_value/<tick_change>', methods=['GET'])
def change_tick_value(tick_change):
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'GET':
        if tick_change == 'increase':
            session['review_tick'] = session['review_tick'] + 1
        elif tick_change == 'decrease':
            session['review_tick'] = session['review_tick'] - 1

        student_past_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_past_data.pickle')
        student_final_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_final_data.pickle')

        session['persona_details'] = student_final_data

        if session['review_tick'] == -1:
            filtered_tick_data = student_past_data[0]
        else:
            filtered_tick_data = student_past_data[session['review_tick']]

        session['past_tick_data_chosen'] = filtered_tick_data

        new_chat_history = load_from_pickle(f'{session["lesson_folder_path"]}/general_chat_history.pickle')

        start_tick = max(0, session['review_tick'] - 15 + 1)

        filtered_chat_history = []

        for i in range(start_tick, session['review_tick'] + 1):
            for j in new_chat_history[i]:
                filtered_chat_history.append(j)

        talking_to = 'default'
        action_chosen = 'default'
        agent_emoticons = [None, None, None, None, None, None]

        if len(filtered_chat_history) != 0:
            element_with_max_tick = max(filtered_chat_history, key=lambda x: x['tick'])

            talking_to = element_with_max_tick['chat_analysis_resp']['talking_to']
            action_chosen = element_with_max_tick['chat_analysis_resp']['action_chosen']
            agent_emoticons = element_with_max_tick['agent_emoticons']

        fin_returned_data = []

        for dict_item in filtered_chat_history:
            dict_item['student_num'] = students_to_numbers[dict_item['guid']]

            fin_returned_data.append(dict_item)

        if session['curr_selected_student'] == -1:
            return jsonify({'chat_history': fin_returned_data,
                            'talking_to': talking_to,
                            'action_chosen': action_chosen,
                            'agent_emoticons': agent_emoticons,
                            'tick': session['review_tick']})

        student_id = numbers_to_students[str(session['curr_selected_student'])]

        if session['review_tick'] == -1:
            return jsonify({'chat_history': fin_returned_data,
                            'emotions': session['past_tick_data_chosen'][student_id]['emotions_original'],
                            'persona_data': session['persona_details'][student_id],
                            'talking_to': talking_to,
                            'action_chosen': action_chosen,
                            'agent_emoticons': agent_emoticons,
                            'tick': session['review_tick']})
        else:
            return jsonify({'chat_history': fin_returned_data,
                            'emotions': session['past_tick_data_chosen'][student_id]['emotions_updated'],
                            'persona_data': session['persona_details'][student_id],
                            'talking_to': talking_to,
                            'action_chosen': action_chosen,
                            'agent_emoticons': agent_emoticons,
                            'tick': session['review_tick']})


@app.route('/get_student_details_in_review/<int:student_number>', methods=['GET'])
def get_student_details_in_review(student_number):
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'GET':
        if student_number == session['curr_selected_student']:
            session['curr_selected_student'] = -1

            return jsonify({'response': 'student unchosen'})

        session['curr_selected_student'] = student_number

        student_id = numbers_to_students[str(session['curr_selected_student'])]

        persona_data = session['persona_details'][student_id]['persona']

        if len(session['past_tick_data_chosen'][student_id]) == 0:
            emotions = {
                'enjoyment': persona_data['enjoyment'],
                'boredom': persona_data['boredom'],
                'anger': persona_data['anger'],
                'anxiety': persona_data['anxiety']
            }

        else:
            if session['review_tick'] == -1:
                emotions = session['past_tick_data_chosen'][student_id]['emotions_original']
            else:
                emotions = session['past_tick_data_chosen'][student_id]['emotions_updated']

        return jsonify({'emotions': emotions,
                        'persona_data': persona_data})


@app.route("/end_review", methods=['POST'])
async def end_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'POST':
        session_data = load_from_pickle(f'{session["lesson_folder_path"]}/session_details.pickle')

        session_data['finished_review'] = True

        session['writing_review'] = True

        dump_to_pickle(f'{session["lesson_folder_path"]}/session_details.pickle', session_data)

        return redirect(url_for('write_review'))


@app.route("/writereview")
async def write_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if 'writing_review' not in session:
        return redirect(url_for('lesson_review'))

    return render_template('write_review.html')


@app.route('/submit_review', methods=['POST'])
async def submit_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'POST':
        json_obj = request.json

        review_text = json_obj['teacher_review_text']

        session_data = load_from_pickle(f'{session["lesson_folder_path"]}/session_details.pickle')

        session_data['review_text'] = review_text

        dump_to_pickle(f'{session["lesson_folder_path"]}/session_details.pickle', session_data)

        logged_in = session['logged_in']
        country_code = session['country_code']
        ip_address = session['ip_address']

        session.clear()

        session['logged_in'] = logged_in
        session['country_code'] = country_code
        session['ip_address'] = ip_address

        session['in_lesson_phase'] = False
        session['in_review_phase'] = False

        return redirect(url_for('phase_select_page'))


""" Check Session Details before accessing Route """
def session_details_check():
    # If country code or logged in don't exist, Route to Root URL
    if 'country_code' not in session or 'logged_in' not in session:
        return redirect(url_for('index'))
    # If country code is not Malta, don't allow access
    elif session['country_code'] != 'MT':
        abort(403)
    # If not Logged In, route to Login Page
    elif not session['logged_in']:
        return redirect(url_for('login'))


if __name__ == "__main__":
    nest_asyncio.apply()
    #asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    #app.run(host="0.0.0.0", port=80, debug=True)
    app.run(host="0.0.0.0", port=64354, debug=True)
    #app.run(host="studentsim.ddns.net", port=64354)

