# -*- coding: utf-8 -*-

from flask import Blueprint, request, url_for, flash, redirect, abort, send_file
from flask import render_template, g
from forms import SurveyForm, EditConsentForm, SectionForm, QuestionForm
from app.models import Survey, Consent, Section
from app.models import Question, QuestionChoice, QuestionNumerical, QuestionText
from app.models import QuestionYN, QuestionLikertScale, QuestionPartTwo, QuestionDecisionOne, \
    QuestionDecisionTwo, QuestionDecisionThree, QuestionDecisionFour, \
    QuestionDecisionFive, QuestionDecisionSix
from app import app, db
from app.decorators import researcher_required, is_section_researcher, belong_researcher
from flask.ext.login import login_user, logout_user, current_user, login_required
import tempfile
from werkzeug import secure_filename
from . import blueprint


@blueprint.route('/')
@blueprint.route('/index')
@login_required
@researcher_required
def index():
    surveys = Survey.query.filter(Survey.researcher==g.user).order_by(Survey.created.desc())
    return render_template('/researcher/index.html',
        tittle = 'Survey',
        surveys = surveys)

@login_required
@researcher_required
@blueprint.route('/survey/new', methods = ['GET', 'POST'])
def new():
    form = SurveyForm()
    if form.validate_on_submit():
        # file = request.files['file']
        # if file:
        filename = secure_filename(form.surveyXml.data.filename)
        if filename:
            tf = tempfile.NamedTemporaryFile()
            form.surveyXml.data.save(tf.name)
            msg = Survey.from_xml(tf.name, g.user)
            tf.close()
            for m in msg:
                flash(m)
            return redirect(url_for('researcher.index'))
        else:
            survey = Survey( title = form.title.data,
                description = form.description.data,
                endDate = form.endDate.data,
                startDate = None,
                maxNumberRespondents = form.maxNumberRespondents.data,
                duration = form.duration.data,
                researcher = g.user)
            db.session.add(survey)
            db.session.commit()
            flash('Your survey have been saved.')
        return redirect(url_for('researcher.editSurvey',id_survey = survey.id))
    return render_template('/researcher/new.html',
        title = 'New survey',
        form = form)


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>', methods = ['GET', 'POST'])
@belong_researcher('survey')
def editSurvey(id_survey):
    #get survey
    survey = Survey.query.get(id_survey)
    sections = survey.sections.all()
    form = SurveyForm()
    if form.validate_on_submit():
        survey.title = form.title.data
        survey.description = form.description.data
        survey.startDate = form.startDate.data
        survey.endDate = form.endDate.data
        survey.maxNumberRespondents = form.maxNumberRespondents.data
        survey.duration = form.duration.data
        db.session.add(survey)
        db.session.commit()
        flash('Your changes have been saved.')
    elif request.method != "POST":
        form.title.data = survey.title
        form.description.data = survey.description
        form.startDate.data = survey.startDate
        form.endDate.data = survey.endDate
        form.maxNumberRespondents.data = survey.maxNumberRespondents
        form.duration.data = survey.duration
    return render_template('/researcher/editSurvey.html',
        title = survey.title,
        form = form,
        survey = survey,
        sections = sections)

@login_required
@researcher_required
@blueprint.route('/survey/deleteSurvey/<int:id_survey>')
@belong_researcher('survey')
def deleteSurvey(id_survey):
    survey = Survey.query.get(id_survey)
    db.session.delete(survey)
    db.session.commit()
    flash('Survey removed')
    return redirect(url_for('researcher.index'))

@login_required
@researcher_required
@blueprint.route('/survey/exportSurvey/<int:id_survey>')
@belong_researcher('survey')
def exportSurvey(id_survey):
    '''http://stackoverflow.com/questions/14614756/how-can-i-generate-file-on-the-fly-and-delete-it-after-download
        http://stackoverflow.com/questions/13344538/how-to-clean-up-temporary-file-used-with-send-file/
    '''
    survey = Survey.query.get(id_survey)
    xml = survey.to_xml()
    tf = tempfile.NamedTemporaryFile()
    xml.write(tf.name,encoding="ISO-8859-1", method="xml")
    flash('Survey exported')
    return send_file(tf, as_attachment=True, attachment_filename=survey.title+'.xml')

def tips_path(section=None):
    '''Return a list with the path of a section
    '''
    l=[]
    if section is not None:
        l.append((section.title, section.id))
        while (section.parent is not None):
            l.append((section.parent.title, section.parent.id))
            section = section.parent
    l.reverse()
    return l


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/consent/add', methods = ['GET', 'POST'])
@belong_researcher('survey')
def addConsent(id_survey):
    form = EditConsentForm()
    survey = Survey.query.get(id_survey)
    consents = survey.consents.all()
    
    if form.validate_on_submit():
        consent = Consent(text = form.text.data,
            survey = survey)
        db.session.add(consent)
        db.session.commit()
        flash('Adding consent.')
        return redirect(url_for('researcher.addConsent',id_survey = survey.id))
 
    return render_template('/researcher/consents.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        consents = consents,
        addConsent = True)


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/consent/<int:id_consent>/delete')
@belong_researcher('consent')
def deleteConsent(id_survey,id_consent):
    consent = Consent.query.get(id_consent)
    db.session.delete(consent)
    db.session.commit()
    flash('consent removed')
    return redirect(url_for('researcher.addConsent',id_survey = id_survey))

@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/consent/<int:id_consent>', methods = ['GET', 'POST'])
@belong_researcher('consent')
def editConsents(id_survey, id_consent):
    consent = Consent.query.get(id_consent)
    form = EditConsentForm()
    if form.validate_on_submit():
        consent.text = form.text.data
        db.session.add(consent)
        db.session.commit()
        flash('Edited consent')
        return redirect(url_for('researcher.addConsent',id_survey = id_survey))
    elif request.method != "POST":
        form.text.data = consent.text
        consents = Consent.query.filter(Consent.survey_id == id_survey)
    return render_template('/researcher/consents.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        consents = consents,
        editConsent = True)


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/section/new', methods = ['GET', 'POST'])
@belong_researcher('survey')
def addSection(id_survey):
    survey = Survey.query.get(id_survey)
    form = SectionForm()
    if form.validate_on_submit():
        section = Section(title = form.title.data,
            description = form.description.data,
            sequence = form.sequence.data,
            percent = form.percent.data,
            survey = survey
            )
        db.session.add(section)
        db.session.commit()
        flash('Adding section.')
        return redirect(url_for('researcher.editSurvey',id_survey = survey.id))
    # heuristics of the next sequence
    section = Section.query.filter(Section.survey_id==id_survey).order_by(Section.sequence.desc())
    if section.count()>=2 and section[0].sequence==section[1].sequence:
        # see the last and  penultimate
        form.sequence.data= section[0].sequence
    elif section.count()>=1:
        form.sequence.data= section[0].sequence + 1
    else:
        form.sequence.data =1
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        survey = survey,
        sections = survey.sections.all(),
        #add = true, you is adding a new section
        addSection = True)


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>', methods = ['GET', 'POST'])
@belong_researcher('section')
def editSection(id_survey, id_section):
    section = Section.query.get(id_section)
    form = SectionForm()
    sections = Survey.query.get(id_survey).sections.all()
    if form.validate_on_submit():
        section.title = form.title.data
        section.description = form.description.data
        section.sequence = form.sequence.data
        section.percent = form.percent.data
        db.session.add(section)
        db.session.commit()
        flash('Save changes')
        return redirect(url_for('researcher.editSection',id_survey = id_survey, id_section = id_section))
    elif request.method != "POST":
        form.title.data = section.title
        form.description.data = section.description
        form.sequence.data = section.sequence
        form.percent.data = section.percent
    path=tips_path(section)
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        survey = Survey.query.get(id_survey),
        sections = sections,
        editSection = True,
        id_section = id_section,
        path = path)


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/deleteSection/<int:id_section>')
@belong_researcher('section')
def deleteSection(id_survey,id_section):
    section = Section.query.get(id_section)
    db.session.delete(section)
    db.session.commit()
    flash('Section removed')
    return redirect(url_for('researcher.editSurvey',id_survey = id_survey))


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>/new', methods = ['GET', 'POST'])
@belong_researcher('section')
def addSubSection(id_survey, id_section):
    parentSection = Section.query.get(id_section)
    form = SectionForm()
    if form.validate_on_submit():
        section = Section(title = form.title.data,
            description = form.description.data,
            sequence = form.sequence.data,
            percent = form.percent.data,
            parent = parentSection)
        db.session.add(section)
        db.session.commit()
        flash('Adding subsection.')
        return redirect(url_for('researcher.editSection',id_survey = id_survey, id_section = id_section))
    # heuristics of the next sequence
    section = Section.query.filter(Section.parent_id==id_section).order_by(Section.sequence.desc())
    if section.count()>=2 and section[0].sequence==section[1].sequence:
        # see the last and  penultimate
        form.sequence.data= section[0].sequence
    elif section.count()>=1:
        form.sequence.data= section[0].sequence + 1
    else:
        form.sequence.data =1
    path=tips_path(parentSection)
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        survey = Survey.query.get(id_survey),
        sections = Survey.query.get(id_survey).sections.all(),
        addSubSection = True,
        path = path)


def selectType(form):

    if form.questionType.data =='yn':
        question = QuestionYN()
    if form.questionType.data == 'numerical':
        question = QuestionNumerical()
    if form.questionType.data == 'text':
        question = QuestionText(isNumber=form.isNumber.data,
            regularExpression=form.regularExpression.data,
            errorMessage=form.errorMessage.data)
    if form.questionType.data == 'choice':
        l = [form.answer1.data,
        form.answer2.data,
        form.answer3.data,
        form.answer4.data,
        form.answer5.data,
        form.answer6.data,
        form.answer7.data,
        form.answer8.data,
        form.answer9.data]
        l_aux=[]
        for i in l:
            if len(i)!=0:
                l_aux.append(i)    
        question = QuestionChoice(choices = l_aux)
    if form.questionType.data == 'likertScale':
        question = QuestionLikertScale(minLikert=form.minLikert.data,
            maxLikert=form.maxLikert.data, labelMin=form.labelMinLikert.data,
            labelMax=form.labelMaxLikert.data)
    if form.questionType.data == 'partTwo':
        l = [form.answer1.data,
        form.answer2.data]
        question = QuestionPartTwo(choices = l[0:2],
            is_real_money=form.is_real_money.data)
    if form.questionType.data == 'decisionOne':
        question = QuestionDecisionOne(is_real_money=form.is_real_money.data)
    if form.questionType.data == 'decisionTwo':
        question = QuestionDecisionTwo(is_real_money=form.is_real_money.data)
    if form.questionType.data == 'decisionThree':
        question = QuestionDecisionThree(is_real_money=form.is_real_money.data)
    if form.questionType.data == 'decisionFour':
        question = QuestionDecisionFour(is_real_money=form.is_real_money.data)
    if form.questionType.data == 'decisionFive':
        l = [form.answer1.data]
        question = QuestionDecisionFive(choices = l[0:1],
            is_real_money=form.is_real_money.data)
    if form.questionType.data == 'decisionSix':
        question = QuestionDecisionSix(is_real_money=form.is_real_money.data)
           
    question.text = form.text.data
    question.required = form.required.data
    question.registerTime = form.registerTime.data
    question.expectedAnswer = form.expectedAnswer.data
    question.maxNumberAttempt = form.maxNumberAttempt.data
    return question



@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>/addQuestion', methods = ['GET', 'POST'])
@belong_researcher('section')
def addQuestion(id_survey, id_section):
    section = Section.query.get(id_section)
    form = QuestionForm()
    if form.validate_on_submit():
        question = selectType(form)

        question.section = section
        db.session.add(question)
        db.session.commit()
        flash('Adding question')
        return redirect(url_for('researcher.addQuestion',id_survey = id_survey, id_section = id_section))
    path=tips_path(section)
    return render_template('/researcher/addEditQuestion.html',
        title = "Question",
        form = form,
        survey = Survey.query.get(id_survey),
        sections = Survey.query.get(id_survey).sections.all(),
        section = section,
        questions = section.questions,
        addQuestion = True,
        type = "yn",
        path = path)


@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>/question/<int:id_question>', methods = ['GET', 'POST'])
@belong_researcher('question')
def editQuestion(id_survey, id_section,id_question):
    question = Question.query.get(id_question)
    form = QuestionForm()    
    if form.validate_on_submit():
        q = selectType(form)
        q.id = question.id
        q.section = question.section
        db.session.delete (question)
        db.session.commit()
        db.session.add(q)
        db.session.commit()
        flash('Adding question')
        return redirect(url_for('researcher.addQuestion',id_survey = id_survey, id_section = id_section))
    elif request.method != "POST":
        form.text.data = question.text
        form.required.data = question.required
        form.registerTime.data = question.registerTime
        form.expectedAnswer.data = question.expectedAnswer
        form.maxNumberAttempt.data = question.maxNumberAttempt
        if isinstance(question, QuestionText):
            form.regularExpression.data = question.regularExpression
            form.isNumber.data = question.isNumber
            form.errorMessage.data = question.errorMessage
        if isinstance (question,QuestionChoice):
            l= question.choices
            if len(l) >0:
                form.answer1.data = l[0]
            if len(l) >1:
                form.answer2.data = l[1]
            if len(l) >2:
                form.answer3.data = l[2]
            if len(l) >3:
                form.answer4.data = l[3]
            if len(l) >4:
                form.answer5.data = l[4]
            if len(l) >5:
                form.answer6.data = l[5]
            if len(l) >6:
                form.answer7.data = l[6]
            if len(l) >7:
                form.answer8.data = l[7]
            if len(l) >8:
                form.answer9.data = l[8]
        if isinstance (question,QuestionPartTwo):
            l= question.choices
            form.answer1.data = l[0]
            form.answer2.data = l[1]
            form.is_real_money.data = question.is_real_money
        if isinstance (question,QuestionDecisionOne):
            form.is_real_money.data = question.is_real_money
        if isinstance (question,QuestionDecisionTwo):
            form.is_real_money.data = question.is_real_money
        if isinstance (question,QuestionDecisionThree):
            form.is_real_money.data = question.is_real_money
        if isinstance (question,QuestionDecisionFour):
            form.is_real_money.data = question.is_real_money
        if isinstance (question,QuestionDecisionFive):
            l= question.choices
            form.answer1.data = l[0]
            form.is_real_money.data = question.is_real_money
        if isinstance (question,QuestionDecisionSix):
            form.is_real_money.data = question.is_real_money

        if isinstance(question, QuestionLikertScale):
            form.labelMinLikert.data=question.labelMin
            form.labelMaxLikert.data=question.labelMax
    section =  Section.query.get(id_section)
    path=tips_path(section)
    return render_template('/researcher/addEditQuestion.html',
        title = "Question",
        form = form,
        survey = Survey.query.get(id_survey),
        sections = Survey.query.get(id_survey).sections.all(),
        section = section,
        questions = Section.query.get(id_section).questions,
        editQuestion = True,
        type = question.type,
        path = path)

@login_required
@researcher_required
@blueprint.route('/survey/<int:id_survey>/Section/<int:id_section>/deleteQuestion/<int:id_question>')
@belong_researcher('question')
def deleteQuestion(id_survey,id_section,id_question):
        #
        #CUANDO TENGA SUBSECCIONES Y ENCUESTAR, EL ELIMINAR NO ES TRIVIAL
        #
    question = Question.query.get(id_question)
    db.session.delete(question)
    db.session.commit()
    flash('Question removed')
    return redirect(url_for('researcher.addQuestion',id_survey = id_survey, id_section=id_section))