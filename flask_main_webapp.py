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


""" Log In, First page accessible by the user before accessing the Experiment """
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


""" Check Login Pass, Checks whether Password entered by User is Correct """
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


""" Phase Selector Page, Accessible after Logging In. Allows User to choose Experiment Phase """
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


""" Choose Phase, Check which Phase was selected and routes to correct page """
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


""" Go back, Sends User back to Phase Selector Page from either Experiment Phase Menu"""
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


""" Detail Entry for Class Simulation, Allows entry of Details, get Unique ID and Start Class Simulation """
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


""" Start Class Simulation, goes through the process of starting the Class Simulation """
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

        # Limit number of concurrent teachers delivering lesson to 5 to reduce risk of system crashing
        if len(session_items_dictionary) > 4:
            return make_response(jsonify({'ok': False, 'message': f'Too many teachers are delivering lessons, try again in 30 minutes.'}), 401)

        # Create Session Data Object with important User Information (to be saved to file)
        session_items_dictionary[username] = SessionData(username, teacher_gender, student_year, ip_address, login_timestamp)

        # Set in_menu and in_lesson variables to signify that User is now in Lesson
        session_items_dictionary[username].in_menu = False
        session_items_dictionary[username].in_lesson = True

        # check whether folder specific for user exists, if not, create it
        check_path_or_create(f'logger/{username}')

        # Save Session Details to file for further analysis
        session_items_dictionary[username].save_session_to_file(username)

        # Redirect to Class Simulation page to show start lesson
        return redirect(url_for('class_simulation'))


""" Class Simulation, displays Class Simulation interface to deliver lesson """
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

        # If username not in session_items_dictionary, then remove username from session and send to detail entry page
        if username not in session_items_dictionary:
            session.pop('username')

            return redirect(url_for('detail_entry_for_class_simulation'))
    # If username not in session, then send to index route
    else:
        return redirect(url_for('index'))

    # Get necessary variables form session_items_dictionary
    in_menu = session_items_dictionary[username].in_menu
    in_lesson = session_items_dictionary[username].in_lesson

    sim = session_items_dictionary[username].simulation

    current_student_value = session_items_dictionary[username].current_student_value
    current_student_talking_to = session_items_dictionary[username].current_student_talking_to
    current_action_chosen = session_items_dictionary[username].current_action_chosen

    portion_of_chat_history = []

    # If in_lesson and not in_menu, then continue process of getting necessary data for class simulation
    if in_lesson and not in_menu:
        # If General Chat History contains more than 20 entries, get first 20 entries
        if len(sim.general_chat_history) > 20:
            for i in range(len(sim.general_chat_history) - 20, len(sim.general_chat_history)):
                for chat_log in sim.general_chat_history[i]:
                    portion_of_chat_history.append(chat_log.to_obj())
        # If General Chat History does not contain more than 20 entries, get all entries
        else:
            for i in range(0, len(sim.general_chat_history)):
                for chat_log in sim.general_chat_history[i]:
                    portion_of_chat_history.append(chat_log.to_obj())

        # Get Currently Active Emoticons
        agent_emoticons = sim.agent_emoticons

        fin_returned_data = []

        # Loop through chat history and assign number for text color
        for i in portion_of_chat_history:
            dict_item = i

            # If Teacher, assign 10 automatically
            if dict_item['guid'] == 'teacher':
                dict_item['student_num'] = 10
            # else, get index of guid within agent list, and assign number
            else:
                dict_item['student_num'] = list(sim.agents).index(
                        dict_item['guid'])

            # Append these to final list of Chat History
            fin_returned_data.append(dict_item)

        # Display general UI if Student Agent isn't selected
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
        # else, if Student agent is selected, then display student details and define which button is selected
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
    # If in menu and not in lesson, then send back to detail entry page
    elif in_menu and not in_lesson:
        return redirect(url_for('detail_entry_for_class_simulation'))


""" Talk to Class, goes through the process of taking user input, and generating response from Student Agents """
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

        # Get Gender and year passed from Front-End
        user_input = json_obj['user_input']
        session_items_dictionary[username].current_student_talking_to = talking_to_chosen = json_obj['talking_to_choice']
        session_items_dictionary[username].current_action_chosen = action_chosen = json_obj['action_choice']

        input_start_time = round(time.time(), 3)

        recent_chat_history = []

        # If Chat History greater than 5, get 5 most recent chat logs
        if len(session_items_dictionary[username].simulation.general_chat_history) > 5:
            for i in range(len(session_items_dictionary[username].simulation.general_chat_history) - 5,
                           len(session_items_dictionary[username].simulation.general_chat_history)):
                for chat_log in session_items_dictionary[username].simulation.general_chat_history[i]:
                    recent_chat_history.append(chat_log)
        # else, get entire Chat History
        else:
            for i in range(0, len(session_items_dictionary[username].simulation.general_chat_history)):
                for chat_log in session_items_dictionary[username].simulation.general_chat_history[i]:
                    recent_chat_history.append(chat_log)

        # Prompt Initial Models to get Necessary Variables for Student Prompting
        game_breaker_resp, question_suitability_resp, chat_analysis_resp = await asyncio.gather(
            run_prompt_and_convert_to_obj('game_breaker_prompt.yaml',
                                          print_prompt=False,
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

        # Check if Responses are Valid, if not then show Error to Class Simulation
        for i in [game_breaker_resp, question_suitability_resp, chat_analysis_resp]:
            if not i['valid']:
                return make_response(jsonify({'ok': False, 'message': i['response'], 'resp_data': None}), 400)

        initial_models_end_time = round(time.time(), 3)

        game_breaker_resp = game_breaker_resp['response']
        question_suitability_resp = question_suitability_resp['response']
        chat_analysis_resp = chat_analysis_resp['response']

        chat_analysis_resp['talking_to'] = talking_to_chosen
        chat_analysis_resp['action_chosen'] = action_chosen

        # If Game Breaker allows User Input, then continue process of generating response from Student Agents
        if game_breaker_resp['allowed']:

            # Go through Simulation Tick, this takes care of the entire Student Agent architecture,
            # from input to generated output
            returned_data = await session_items_dictionary[username].simulation.tick(user_input,
                                                                                     input_start_time,
                                                                                     chat_analysis_resp,
                                                                                     question_suitability_resp)

            tick_end_time = round(time.time(), 3)

            # If returned_data gets a response which is invalid, then show this in the Class Simulation.
            if not returned_data['valid']:
                return make_response(jsonify({'ok': False, 'message': returned_data['response'], 'resp_data': None}), 400)

            returned_data = returned_data['response']

            fin_returned_data = []

            # For each returned data, get index of guid within agent list, and assign number for text color
            for i in returned_data:
                dict_item = i

                dict_item['student_num'] = list(session_items_dictionary[username].simulation.agents).index(dict_item['agent_guid'])

                fin_returned_data.append(dict_item)

            agent_emoticons = session_items_dictionary[username].simulation.agent_emoticons

            teacher_id = session_items_dictionary[username].teacher_id

            # Save data (Snapshots just in case an issue occurs during lesson delivery
            await session_items_dictionary[username].simulation.save_data(teacher_id)

            # Return the Responses generated by students, and their corresponding emoticons
            return make_response(jsonify({'ok': True, 'message': 'Successful', 'resp_data': {'new_text': returned_data, 'new_agent_emoticons': agent_emoticons}}), 200)
        # If Game Breaker doesn't allow User Input, deny and show reason to User
        else:
            return make_response(jsonify({'ok': False, 'message': f'Input not Allowed: {game_breaker_resp["reason"]}'}), 400)


""" Get Student Details, gets the details of the student clicked on within the Class Simulation """
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
        # If Student Chosen is already selected, then remove the selection
        if student_number == session_items_dictionary[username].current_student_value:
            session_items_dictionary[username].current_student_value = -1

            return jsonify({'response': 'student unchosen'})

        # Save student number of Student Chosen to Session
        session_items_dictionary[username].current_student_value = student_number

        # Error Handling when testing with less than 6 students
        if student_number > (len(agents)-1):
            return jsonify({"message": "Error", "dataNumber": 'no student found'})

        # Get Data of selected Student
        curr_selected_student = agents[list(agents)[student_number]]

        # Return Student Persona data to Class Simulation
        return jsonify(curr_selected_student.persona.to_obj())


""" End Lesson, Saves the data, removes session details and routes User back to Phase Selector Page """
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

        # Set Session variables accordingly to go back to menu
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

        # Remove User from session_items_dictionary
        if username in session_items_dictionary:
            session_items_dictionary.pop(username)

        # Keep important login variables to avoid making user login again
        logged_in = session['logged_in']
        country_code = session['country_code']
        ip_address = session['ip_address']

        # Clear Session Data
        session.clear()

        # Place them back into Session
        session['logged_in'] = logged_in
        session['country_code'] = country_code
        session['ip_address'] = ip_address
        """ Save to file and Delete Teacher Session Details """

        # Route user to Phase Select Page
        return redirect(url_for('phase_select_page'))


""" Get Lesson for Review, Gets all available lesson from review within Logger Folder and loads Page to start Review """
@app.route("/getlessonforreview")
async def get_lesson_for_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if 'in_lesson_phase' in session and 'in_review_phase' in session:
        # If in Review Phase, then continue process
        if session['in_review_phase']:

            if 'in_review' in session:
                if session['in_review']:
                    return redirect(url_for('lesson_review'))

            folder_path = f'logger'

            general_list_of_lessons = []
            list_of_lessons_for_review = []

            # Loop through all Users saved in Logger Folder
            for i in os.listdir(folder_path):
                curr_path = f'{folder_path}/{i}/session_details.pickle'

                # Load Session Pickle
                session_data = load_from_pickle(curr_path)

                # Append teacher_id to list of lessons found
                general_list_of_lessons.append(session_data['teacher_id'])

                # If Lesson is finished, it hasn't been reviewed yet and it isn't currently being reviewed,
                # then add it to list of lessons able to be reviewed
                if session_data['finished_lesson'] and not session_data['finished_review'] and not session_data['currently_being_reviewed']:
                    list_of_lessons_for_review.append(session_data['teacher_id'])

            session['general_list_of_lessons'] = general_list_of_lessons
            session['list_of_lessons_for_review'] = list_of_lessons_for_review

            return render_template('get_lesson_for_review_menu.html')
        # If in lesson phase, then sent to menu for class simulation
        elif session['in_lesson_phase']:
            return redirect(url_for('detail_entry_for_class_simulation'))
        # Else, send to initial phase selector page
        else:
            return redirect(url_for('phase_select_page'))
    # Send to Phase Selector Page if missing in_lesson_phase and in_review_phase
    else:
        return redirect(url_for('phase_select_page'))


""" Start Lesson Review, Goes through the process of Randomly Selecting a Lesson for Review """
@app.route("/start_lesson_review", methods=['POST'])
async def start_lesson_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'POST':
        json_obj = request.json

        # Get Teacher ID assigned in get_lesson_for_review menu
        id_inputted = json_obj['teacher_id']

        list_of_lessons_for_review = session['list_of_lessons_for_review']

        # If id inputted by user is both in general and reviewable list of lesson, then remove from reviewable list
        if id_inputted in session['general_list_of_lessons']:
            if id_inputted in session['list_of_lessons_for_review']:
                list_of_lessons_for_review.remove(id_inputted)
        # If not found in general list of lessons, then send error showing that ID does not exist
        else:
            return make_response(jsonify({'ok': False, 'message': 'ID does not Exist, Try Again.'}), 401)

        # Keep on looping until lesson which isn't already reviewed is found or until run out of lessons
        while True:
            # if no lessons left in list of lessons for review, then return "No Lessons left to Review"
            if len(list_of_lessons_for_review) == 0:
                return make_response(jsonify({'ok': False, 'message': 'No Lessons Left to Review.'}), 401)

            # Randomly Choose a teacher id (does not include inputted teacher id)
            chosen_id = random.choice(list_of_lessons_for_review)

            session['teacher_id'] = id_inputted

            curr_path = f'logger/{chosen_id}'

            session['lesson_folder_path'] = curr_path

            # Get Session Data of chosen Teacher ID
            session_data_for_review = load_from_pickle(f'{curr_path}/session_details.pickle')

            # If it is currently being reviewed, ten remove it from list of reviewable lessons
            if session_data_for_review['currently_being_reviewed']:
                list_of_lessons_for_review.remove(chosen_id)
            else:
                # Save teacher id to session
                session['lesson_name'] = chosen_id

                # Change Session Data for chosen lesson
                session_data_for_review['currently_being_reviewed'] = True
                session_data_for_review['reviewed_by'] = session['teacher_id']

                # Save Session Data to "lock" the lesson
                dump_to_pickle(f'{curr_path}/session_details.pickle', session_data_for_review)

                # Stop While True Loop
                break

        # Define necessary variables for reviewing in Session
        session['student_folder_paths'] = []
        session['past_tick_data'] = {}
        session['persona_details'] = {}
        session['review_tick'] = -1
        session['curr_selected_student'] = -1
        session['action_taken'] = -1
        session['in_review'] = True

        # Route user to Lesson Review Page
        return redirect(url_for("lesson_review"))


""" Lesson Review, displays the User Interface to review lesson"""
@app.route("/lessonreview")
async def lesson_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    # If in_lesson_phase and in_review_phase exist in Session, then continue process
    if 'in_lesson_phase' in session and 'in_review_phase' in session:
        if session['in_review_phase']:

            # If cannot find lesson_name, then send to previous menu to enter details for lesson review
            if 'lesson_name' not in session:
                return redirect(url_for('get_lesson_for_review'))
            # If User is writing review, then send to the Write Review page
            if 'writing_review' in session:
                if session['writing_review']:
                    return redirect(url_for('write_review'))

            # Load Session, Student Past and Student Present Data
            session_data = load_from_pickle(f'{session["lesson_folder_path"]}/session_details.pickle')
            student_past_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_past_data.pickle')
            student_final_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_final_data.pickle')

            # Save Persona Details from Student Final Data to Session
            session['persona_details'] = student_final_data

            # If Review Tick is 0 in Front-End, then get first entry in Student Past Data
            if session['review_tick'] == -1:
                filtered_tick_data = student_past_data[0]
            # Else, get Past Data of Specific Tick chosen
            else:
                filtered_tick_data = student_past_data[session['review_tick']]

            # Save this into Session
            session['past_tick_data_chosen'] = filtered_tick_data

            # Load Chat History
            new_chat_history = load_from_pickle(f'{session["lesson_folder_path"]}/general_chat_history.pickle')

            # Calculate the starting tick for Chat History (Loading the past 15 chat logs instead of whole chat log constantly)
            start_tick = max(0, session['review_tick'] - 15 + 1)

            filtered_chat_history = []

            # Get all ticks from n-15 to n, with n being current tick
            for i in range(start_tick, session['review_tick'] + 1):
                for j in new_chat_history[i]:
                    # Save these chat logs into array to display
                    filtered_chat_history.append(j)

            # Set default values
            talking_to = 'default'
            action_chosen = 'default'
            agent_emoticons = [None, None, None, None, None, None]

            # If Filtered Chat History contains Chat Logs, then assign values of max tick, aka get talking_to, action_chosen
            # and agent emoticons of tick currently chosen
            if len(filtered_chat_history) != 0:
                element_with_max_tick = max(filtered_chat_history, key=lambda x: x['tick'])

                talking_to = element_with_max_tick['chat_analysis_resp']['talking_to']
                action_chosen = element_with_max_tick['chat_analysis_resp']['action_chosen']
                agent_emoticons = element_with_max_tick['agent_emoticons']

            fin_returned_data = []

            # For each Chat Log in Chat History, assign numbers for Colours in User Interface
            for dict_item in filtered_chat_history:
                dict_item['student_num'] = students_to_numbers[dict_item['guid']]

                fin_returned_data.append(dict_item)

            # If a Student isn't selected, then return empty Student Data
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
            # Else, if Student is Selected, then go through process of getting Student Data
            else:
                # Convert Student Number to Student ID of Current Student Selected
                student_id = numbers_to_students[str(session['curr_selected_student'])]

                # Get Persona data of that specific student
                persona_data = session['persona_details'][student_id]['persona']

                # If Review tick is equal to Student Past Data, then get most recent Emotions
                # This is only activated when max Review Tick is Reached
                if session['review_tick'] == len(student_past_data):
                    emotions = {
                        'enjoyment': persona_data['enjoyment'],
                        'boredom': persona_data['boredom'],
                        'anger': persona_data['anger'],
                        'anxiety': persona_data['anxiety']
                    }
                else:
                    # If User Interface is not showing and Review Ticks (aka Review Tick is 0 in UI), then display
                    # original emotions
                    if session['review_tick'] == -1:
                        emotions = session['past_tick_data_chosen'][student_id]['emotions_original']
                    # Else, get updated emotions
                    else:
                        emotions = session['past_tick_data_chosen'][student_id]['emotions_updated']

                # Render Page containing all details of Selected Student, including name, age, gender, emotions, etc.
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
        # If in Lesson Phase, then send to Detail Entry for Class Simulation Page
        elif session['in_lesson_phase']:
            return redirect(url_for('detail_entry_for_class_simulation'))
        # Else, send to Phase Selector
        else:
            return redirect(url_for('phase_select_page'))


""" Change Tick Value, Either See Next or Previous Review Tick Data """
@app.route('/change_tick_value/<tick_change>', methods=['GET'])
def change_tick_value(tick_change):
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'GET':
        # Increase / Decrease Review Tick based choice of User reviewing the lesson
        if tick_change == 'increase':
            session['review_tick'] = session['review_tick'] + 1
        elif tick_change == 'decrease':
            session['review_tick'] = session['review_tick'] - 1

        # Reload Past and Final Student Data
        student_past_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_past_data.pickle')
        student_final_data = load_from_pickle(f'{session["lesson_folder_path"]}/student_final_data.pickle')

        # Save Final Data into Session
        session['persona_details'] = student_final_data

        # If new Review Tick is 0 in Front-End, then get first entry in Student Past Data
        if session['review_tick'] == -1:
            filtered_tick_data = student_past_data[0]
        # Else, get Past Data of Specific Tick chosen
        else:
            filtered_tick_data = student_past_data[session['review_tick']]

        session['past_tick_data_chosen'] = filtered_tick_data

        new_chat_history = load_from_pickle(f'{session["lesson_folder_path"]}/general_chat_history.pickle')

        # Calculate the starting tick for Chat History (Loading the past 15 chat logs instead of whole chat log constantly)
        start_tick = max(0, session['review_tick'] - 15 + 1)

        filtered_chat_history = []

        # Get all ticks from n-15 to n, with n being current tick
        for i in range(start_tick, session['review_tick'] + 1):
            for j in new_chat_history[i]:
                # Save these chat logs into array to display
                filtered_chat_history.append(j)

        # Set default values
        talking_to = 'default'
        action_chosen = 'default'
        agent_emoticons = [None, None, None, None, None, None]

        # If Filtered Chat History contains Chat Logs, then assign values of max tick, aka get talking_to, action_chosen
        # and agent emoticons of tick currently chosen
        if len(filtered_chat_history) != 0:
            element_with_max_tick = max(filtered_chat_history, key=lambda x: x['tick'])

            talking_to = element_with_max_tick['chat_analysis_resp']['talking_to']
            action_chosen = element_with_max_tick['chat_analysis_resp']['action_chosen']
            agent_emoticons = element_with_max_tick['agent_emoticons']

        fin_returned_data = []

        # For each Chat Log in Chat History, assign numbers for Colours in User Interface
        for dict_item in filtered_chat_history:
            dict_item['student_num'] = students_to_numbers[dict_item['guid']]

            fin_returned_data.append(dict_item)

        # If a Student isn't selected, then return empty Student Data
        if session['curr_selected_student'] == -1:
            # Return necessary data to change User Interface
            return jsonify({'chat_history': fin_returned_data,
                            'talking_to': talking_to,
                            'action_chosen': action_chosen,
                            'agent_emoticons': agent_emoticons,
                            'tick': session['review_tick']})

        # Convert Student Number to Student ID of Current Student Selected
        student_id = numbers_to_students[str(session['curr_selected_student'])]

        # If Review Tick is 0, then send Initial Emotions
        if session['review_tick'] == -1:
            return jsonify({'chat_history': fin_returned_data,
                            'emotions': session['past_tick_data_chosen'][student_id]['emotions_original'],
                            'persona_data': session['persona_details'][student_id],
                            'talking_to': talking_to,
                            'action_chosen': action_chosen,
                            'agent_emoticons': agent_emoticons,
                            'tick': session['review_tick']})
        # Else, send Updated Emotions of tick
        else:
            return jsonify({'chat_history': fin_returned_data,
                            'emotions': session['past_tick_data_chosen'][student_id]['emotions_updated'],
                            'persona_data': session['persona_details'][student_id],
                            'talking_to': talking_to,
                            'action_chosen': action_chosen,
                            'agent_emoticons': agent_emoticons,
                            'tick': session['review_tick']})


""" Get Student Details in Review, gets the details of the student clicked on within the Lesson Review"""
@app.route('/get_student_details_in_review/<int:student_number>', methods=['GET'])
def get_student_details_in_review(student_number):
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'GET':
        # If Selected Student is the same as Currently Selected Student, then "Unselect" Student
        if student_number == session['curr_selected_student']:
            session['curr_selected_student'] = -1

            return jsonify({'response': 'student unchosen'})

        session['curr_selected_student'] = student_number

        # Convert Number of Selected Student to Student Number
        student_id = numbers_to_students[str(session['curr_selected_student'])]

        # Get Persona Data of newly Selected Student
        persona_data = session['persona_details'][student_id]['persona']

        # If Student doesn't contain Past Data, then assign Emotions using Persona Data
        if len(session['past_tick_data_chosen'][student_id]) == 0:
            emotions = {
                'enjoyment': persona_data['enjoyment'],
                'boredom': persona_data['boredom'],
                'anger': persona_data['anger'],
                'anxiety': persona_data['anxiety']
            }
        else:
            # If Review Tick is 0 in Front End, then show original emotions
            if session['review_tick'] == -1:
                emotions = session['past_tick_data_chosen'][student_id]['emotions_original']
            # Else, show Updated Emotions for Each Tick
            else:
                emotions = session['past_tick_data_chosen'][student_id]['emotions_updated']

        # Return new Emotions and Persona Data
        return jsonify({'emotions': emotions,
                        'persona_data': persona_data})


""" End Review, Goes through the process of ending the Review """
@app.route("/end_review", methods=['POST'])
async def end_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'POST':
        # Load Session Data
        session_data = load_from_pickle(f'{session["lesson_folder_path"]}/session_details.pickle')

        # Edit Data to reflect the review being finished on the lesson and that the User is currently writing the review
        session_data['finished_review'] = True

        session['writing_review'] = True

        # Save newly edited Session Data
        dump_to_pickle(f'{session["lesson_folder_path"]}/session_details.pickle', session_data)

        # Route User to Write Review Page
        return redirect(url_for('write_review'))


""" Write Review, displays the User Interface to write the review for the lesson """
@app.route("/writereview")
async def write_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    # If writing_review is not in Session, the route back to the Lesson Review page
    if 'writing_review' not in session:
        return redirect(url_for('lesson_review'))

    # Display Write Review Page
    return render_template('write_review.html')


""" Submit Review, goes through the process of Saving the Review and sending the User back to the Main Menu"""
@app.route('/submit_review', methods=['POST'])
async def submit_review():
    # Check Session Details for country_code and logged_in
    check_result = session_details_check()

    # If session_details_check returned something, return it and don't proceed with loading page
    if check_result:
        return check_result

    if request.method == 'POST':
        json_obj = request.json

        # Get Review Text Submitted from Front End
        review_text = json_obj['teacher_review_text']

        # Load Session Data
        session_data = load_from_pickle(f'{session["lesson_folder_path"]}/session_details.pickle')

        # Set Review Text in Session Data
        session_data['review_text'] = review_text

        # Save new Session Data
        dump_to_pickle(f'{session["lesson_folder_path"]}/session_details.pickle', session_data)

        # Save important Session data to allow the User to stay logged in
        logged_in = session['logged_in']
        country_code = session['country_code']
        ip_address = session['ip_address']

        # Clear Session
        session.clear()

        session['logged_in'] = logged_in
        session['country_code'] = country_code
        session['ip_address'] = ip_address

        # Set in_lesson_phase and in_review_phase to False
        session['in_lesson_phase'] = False
        session['in_review_phase'] = False

        # Route User to Phase Select Page
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
    app.run(host="0.0.0.0", port=80, debug=True)
    #app.run(host="studentsim.ddns.net", port=64354)

