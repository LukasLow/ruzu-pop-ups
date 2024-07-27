# Copyright 2020 Charles Henry
import aqt
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    # Pfad zur Log-Datei
    log_file_path = '/Users/lukas/Library/Application Support/Anki2/addons21/ruzu_pop_ups/log.txt'
    
    # Erstelle das Verzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    
    # Konfiguriere den Logger
    logger = logging.getLogger('AnkiLogger')
    logger.setLevel(logging.DEBUG)
    
    # Entferne alle existierenden Handler, um doppelte Einträge zu vermeiden
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Erstelle einen RotatingFileHandler mit UTF-8 Kodierung
    handler = RotatingFileHandler(log_file_path, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')  # 5 MB pro Datei, bis zu 5 Backups
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Rufe setup_logger auf, um den Logger zu konfigurieren
logger = setup_logger()

class AnkiUtils:

    def main_window(self):
        return aqt.mw

    def reviewer(self):
        reviewer = self.main_window().reviewer
        if reviewer is None:
            raise Exception('There was an issue getting the reviewer')
        else:
            return reviewer

    def collection(self):
        collection = self.main_window().col
        if collection is None:
            raise Exception('There was an issue getting the collection')
        else:
            return collection

    def selected_deck(self):
        return self.main_window()._selectedDeck()['name']

    def get_decks(self):
        decks = self.collection().decks
        if decks is None:
            raise Exception('There was an issue getting the decks')
        else:
            return decks.all_names_and_ids()

    def scheduler(self):
        scheduler = self.collection().sched
        if scheduler is None:
            raise Exception('There was an issue getting the scheduler')
        else:
            return scheduler

    def review_is_active(self):
        return self.reviewer().card is not None and self.main_window().state == 'review'

    def show_question(self):
        if self.review_is_active():
            card = self.reviewer().card
            question_html = self.reviewer()._mungeQA(card.q())
            logger.debug(f'Frage HTML: {question_html}')
            return question_html
        else:
            return None

    def show_answer(self):
        if self.review_is_active():
            card = self.reviewer().card
            answer_html = self.reviewer()._mungeQA(card.a())
            logger.debug(f'Antwort HTML: {answer_html}')
            return answer_html
        else:
            return None

    def answer_card(self, ease):
        if not self.review_is_active():
            return False

        reviewer = self.reviewer()
        if reviewer.state != 'answer':
            return False
        if ease <= 0 or ease > self.scheduler().answerButtons(reviewer.card):
            return False

        reviewer._answerCard(ease)
        return True

    def move_to_overview_state(self, name):
        collection = self.collection()
        if collection is not None:
            deck = collection.decks.by_name(name)
            if deck is not None:
                collection.decks.select(deck['id'])
                try:
                    self.main_window().onOverview()
                except AttributeError:
                    pass
                return True

        return False

    def move_to_review_state(self, name):
        if self.move_to_overview_state(name):
            self.main_window().moveToState('review')
            return True
        else:
            return False

    def get_question(self, card):
        if getattr(card, 'question', None) is None:
            question = card._getQA()['q']
        else:
            question = card.question()
        return question

    def get_answer(self, card):
        if getattr(card, 'answer', None) is None:
            answer = card._getQA()['a']
        else:
            answer = card.answer()
        return answer

    def get_current_card(self):
        logger.debug('get_current_card: Überprüfe, ob Review aktiv ist...')
        
        if not self.review_is_active():
            logger.error('Review ist nicht aktiv. Keine Karte kann abgerufen werden.')
            raise Exception('There was an issue getting the current card because review is not currently active.')
        
        logger.debug('Review ist aktiv. Abhole Reviewer-Objekt...')
        reviewer = self.reviewer()
        
        if reviewer.card is None:
            logger.error('Keine Karte gefunden. Das Reviewer-Objekt enthält keine Karte.')
            raise Exception('No card found in the reviewer object.')
        
        card = reviewer.card
        note_type = card.note_type()
        
        logger.debug(f'Karte gefunden: ID={card.id}')
        logger.debug(f'Frage der Karte: {self.get_question(card)}')
        
        try:
            # Frage und Antwort HTML richtig bearbeiten
            question_html = self.show_question()  # Verwendung der Methode show_question
            answer_html = self.show_answer()      # Verwendung der Methode show_answer
            
            # Falls es einen Platzhalter für typed answers gibt
            if "{{type:" in question_html:
                logger.debug("Typed answer field detected, processing...")
                reviewer.typeAnsQuestion = card.q()
                reviewer.typeAnsAnswer = card.a()
                reviewer._showAnswer()  # Zeigt die Antwort mit dem Tippfeld an
                
                # Aktualisiere das gerenderte HTML der Frage
                question_html = self.show_question()
                
                # Ersetze den Platzhalter für das Eingabefeld auf der Rückseite mit der Benutzereingabe
                answer_html = self.show_answer()
                if "{{type:" in answer_html:
                    user_input = reviewer.typedText
                    answer_html = answer_html.replace('{{type:}}', user_input)

            css = note_type['css']
            button_list = reviewer._answerButtonList()
            
            response = {
                'card_id': card.id,
                'question': question_html,
                'answer': answer_html,
                'css': css,
                'button_list': button_list
            }
            
            logger.debug(f'Antwort-Objekt erstellt: {response}')
            
        except Exception as e:
            logger.error(f'Fehler beim Abrufen der Karteninformationen: {str(e)}')
            raise
        
        return response

    def get_config(self):
        # Do some checks to ensure the config is valid
        config = self.main_window().addonManager.getConfig(__name__.split('.')[0])
        if not config:
            raise Exception('Config file seems to be invalid, correct or restore default config to resolve this issue.')
        return config

    def set_config(self, config):
        self.main_window().addonManager.writeConfig(__name__.split('.')[0], config)
