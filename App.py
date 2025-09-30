
import streamlit as st
import pandas as pd
import base64, random
import datetime
import pymysql
import os, socket, platform, secrets, io
import geocoder
from geopy.geocoders import Nominatim
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
from streamlit_tags import st_tags
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import nltk
from groq import Groq   # ✅ Groq client

nltk.download('stopwords')

# Initialize Groq client
client = Groq(api_key="hgjhy")


###### Database Setup ######
connection = pymysql.connect(host='localhost', user='root', password='12345', db='resume_analyzer')
cursor = connection.cursor()

# Insert user data
def insert_data(sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
                act_name, act_mail, act_mob, cand_name, cand_email, res_score, timestamp, no_of_pages,
                reco_field, cand_level, skills, recommended_skills, courses, pdf_name):
    insert_sql = """INSERT INTO user_data
    (sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
     act_name, act_mail, act_mob, cand_name, cand_email, res_score, timestamp, no_of_pages,
     reco_field, cand_level, skills, recommended_skills, courses, pdf_name)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    rec_values = (str(sec_token), str(ip_add), host_name, dev_user, os_name_ver, str(latlong), city, state, country,
                  act_name, act_mail, act_mob, cand_name, cand_email, str(res_score), timestamp, str(no_of_pages),
                  reco_field, cand_level, str(skills), str(recommended_skills), str(courses), pdf_name)
    cursor.execute(insert_sql, rec_values)
    connection.commit()

# Insert feedback
def insert_feedback(name, email, feedback, score=5):
    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    cursor.execute(
        "INSERT INTO user_feedback (feed_name, feed_email, feed_score, comments, timestamp) VALUES (%s, %s, %s, %s, %s)",
        (name, email, score, feedback, ts)
    )
    connection.commit()

###### Helper Functions ######
def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def course_recommender(course_list):
    st.subheader("**Courses & Certificates Recommendations 👨‍🎓**")
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 5)
    random.shuffle(course_list)
    for i, (c_name, c_link) in enumerate(course_list, 1):
        st.markdown(f"({i}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if i == no_of_reco:
            break
    return rec_course

# ✅ Groq Q&A
def ask_groq(question, resume_text):
    prompt = f"""
    The following text is extracted from a resume:

    {resume_text}

    Question: {question}

    Please answer in a clear, professional, and concise way.
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

###### Streamlit Config ######
st.set_page_config(page_title="AI Resume Analyzer", page_icon='./Logo/recommend.png')

###### Main Function ######
def run():
    st.sidebar.markdown("# Choose Something...")
    activities = ["User", "Feedback", "About", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)

    ###### USER PAGE ######
    if choice == 'User':
        st.title("AI Resume Analyzer 📝")

        # Collecting User Info
        act_name = st.text_input('Name*')
        act_mail = st.text_input('Mail*')
        act_mob = st.text_input('Mobile Number*')

        sec_token = secrets.token_urlsafe(12)
        host_name = socket.gethostname()
        ip_add = socket.gethostbyname(host_name)
        dev_user = os.getlogin()
        os_name_ver = platform.system() + " " + platform.release()
        g = geocoder.ip('me')
        latlong = g.latlng if g.latlng else ["NA", "NA"]
        geolocator = Nominatim(user_agent="http")
        try:
            location = geolocator.reverse(latlong, language='en')
            address = location.raw['address']
            city = address.get('city', '')
            state = address.get('state', '')
            country = address.get('country', '')
        except:
            city, state, country = '', '', ''

        st.subheader("Upload Your Resume 📂")
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])

        job_choice = st.selectbox("Select your desired Job Role:", 
                                  ["Select", "Data Science", "Web Development", "Android Development", "iOS Development", "UI/UX Design"])

        # Mandatory skills dictionary
        mandatory_skills = {
            "Data Science": ["Python", "Machine Learning", "Statistics", "Pandas", "Numpy"],
            "Web Development": ["HTML", "CSS", "JavaScript", "React", "Django"],
            "Android Development": ["Java", "Kotlin", "XML", "Android Studio"],
            "iOS Development": ["Swift", "Xcode", "Objective-C"],
            "UI/UX Design": ["Figma", "Adobe XD", "Wireframing", "Prototyping"]
        }

        # Show mandatory skills immediately
        if job_choice != "Select":
            st.info(f"Mandatory skills for **{job_choice}**: {', '.join(mandatory_skills[job_choice])}")

        if pdf_file is not None:
            save_path = './Uploaded_Resumes/' + pdf_file.name
            pdf_name = pdf_file.name
            with open(save_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_path)

            resume_data = ResumeParser(save_path).get_extracted_data()
            if resume_data:
                resume_text = pdf_reader(save_path)

                st.header("**Resume Analysis 🤘**")
                st.success("Hello " + resume_data.get('name', 'User'))

                # Candidate Level
                cand_level = "Fresher"
                if 'EXPERIENCE' in resume_text.upper():
                    cand_level = "Experienced"
                elif 'INTERNSHIP' in resume_text.upper():
                    cand_level = "Intermediate"
                st.subheader(f"**Expertise Level:** {cand_level}")

                # Skills
                skills = resume_data.get('skills', [])
                st_tags(label='### Your Current Skills', text='Skills extracted from your resume',
                        value=skills, key='1')

                # ✅ Recommended skills (missing ones)
                if job_choice != "Select":
                    missing_skills = [s for s in mandatory_skills[job_choice] if s.lower() not in [x.lower() for x in skills]]
                    if missing_skills:
                        st.warning(f"⚠️ Recommended Skills for {job_choice}: {', '.join(missing_skills)}")
                    else:
                        st.success("🎉 You already have all the mandatory skills for your chosen role!")

                # Resume Score
                resume_score = 0
                if 'OBJECTIVE' in resume_text.upper() or 'SUMMARY' in resume_text.upper():
                    resume_score += 10
                if 'EDUCATION' in resume_text.upper():
                    resume_score += 10
                if 'PROJECT' in resume_text.upper():
                    resume_score += 20
                if 'CERTIFICATION' in resume_text.upper():
                    resume_score += 10
                if 'SKILL' in resume_text.upper():
                    resume_score += 10
                if 'EXPERIENCE' in resume_text.upper():
                    resume_score += 20
                if 'INTERNSHIP' in resume_text.upper():
                    resume_score += 10

                st.subheader("**Resume Score 📝**")
                st.progress(resume_score)
                st.success(f"Your Resume Score: {resume_score}/100")

                # Save to DB
                ts = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
                insert_data(sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
                            act_name, act_mail, act_mob, resume_data.get('name', ''), resume_data.get('email', ''),
                            resume_score, ts, resume_data.get('no_of_pages', 1),
                            job_choice, cand_level, skills, missing_skills, [], pdf_name)

                # Courses
                if job_choice == "Data Science":
                    course_recommender(ds_course)
                elif job_choice == "Web Development":
                    course_recommender(web_course)
                elif job_choice == "Android Development":
                    course_recommender(android_course)
                elif job_choice == "iOS Development":
                    course_recommender(ios_course)
                elif job_choice == "UI/UX Design":
                    course_recommender(uiux_course)

                # Resume & Interview Videos
                st.header("**Resume Tips Video 💡**")
                st.video(random.choice(resume_videos))
                st.header("**Interview Preparation Video 💡**")
                st.video(random.choice(interview_videos))

                # ✅ Groq Q&A Section
                st.header("💬 Ask AI About Your Resume")
                user_question = st.text_input("Ask a question about your resume, job role, or interview prep:")
                if st.button("Ask"):
                    if user_question:
                        with st.spinner("AI is thinking..."):
                            answer = ask_groq(user_question, resume_text)
                        st.success(answer)

    ###### FEEDBACK PAGE ######
    elif choice == 'Feedback':
        st.title("Feedback Form 💬")
        name = st.text_input("Your Name")
        email = st.text_input("Your Email")
        feedback = st.text_area("Your Feedback")
        score = st.slider("Rate us (1-5)", 1, 5)

        if st.button("Submit Feedback"):
            if name and email and feedback:
                insert_feedback(name, email, feedback, score)
                st.success("✅ Thank you for your feedback!")
            else:
                st.error("⚠️ Please fill all fields before submitting.")

    ###### ABOUT PAGE ######
    elif choice == 'About':
        st.info("This is an AI-powered Resume Analyzer built using NLP + Groq AI + Streamlit.")

    ###### ADMIN PAGE ######
    elif choice == 'Admin':
        st.title("Admin Login 🔑")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username == "admin" and password == "1234":
                st.success("Welcome Admin!")

                cursor.execute("SELECT act_name, act_mail, cand_name, cand_email, skills, recommended_skills FROM user_data")
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=["User Name", "User Email", "Candidate Name", "Candidate Email", "Skills", "Recommended Skills"])
                st.subheader("User Data 📊")
                st.dataframe(df)

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "user_data.csv", "text/csv")

                cursor.execute("SELECT * FROM user_feedback")
                fb = cursor.fetchall()
                if fb:
                    fb_df = pd.DataFrame(fb, columns=["ID","Name","Email","Score","Feedback","Timestamp"])
                    st.subheader("User Feedback 💬")
                    st.dataframe(fb_df)
            else:
                st.error("Invalid username or password!")

# Run
if __name__ == "__main__":
    run()