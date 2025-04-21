import os
import base64
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
import io
import tempfile
import requests
import json
from dotenv import load_dotenv
import urllib3

# Désactiver les avertissements liés à la désactivation de la vérification SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Chargement des variables d'environnement
load_dotenv()

def convert_pdf_to_images(pdf_path, dpi=300):
    """
    Convertit un PDF en une liste d'images
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        dpi: Résolution des images (plus élevé = meilleure qualité mais fichiers plus grands)
        
    Returns:
        list: Liste d'objets PIL Image
    """
    try:
        # Essayer d'abord avec Poppler dans le PATH du système
        try:
            # Utiliser pdf2image sans spécifier le chemin Poppler (utilise le PATH système)
            images = convert_from_path(pdf_path, dpi=dpi)
            return images
        except Exception as path_error:
            print(f"Poppler non trouvé dans le PATH, tentative avec le chemin spécifique: {path_error}")
            
            # Chemin vers les binaires Poppler (chemin spécifique en fallback)
            # Ancien chemin temporaire (commenté) : r"C:\poppler\poppler-24.08.0\Library\bin"
            # Utiliser le chemin système
            poppler_path = r"C:\Program Files\poppler\bin"
            
            # Utiliser pdf2image pour convertir le PDF en images en spécifiant le chemin vers Poppler
            images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
            return images
    except Exception as e:
        print(f"Erreur lors de la conversion du PDF en images: {e}")
        return []

def encode_image_to_base64(image):
    """
    Encode une image PIL en base64 pour l'envoi à l'API
    
    Args:
        image: Objet PIL Image
        
    Returns:
        str: Chaîne base64 de l'image
    """
    # Convertir l'image en bytes
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=80) # Qualité réduite pour limiter la taille
    img_bytes = buffered.getvalue()
    
    # Encoder en base64
    return base64.b64encode(img_bytes).decode('utf-8')

def extract_text_from_pdf(pdf_path):
    """
    Méthode de secours pour extraire le texte d'un fichier PDF si l'API Vision échoue
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte du PDF: {e}")
        text = "Erreur lors de l'extraction du texte du CV"
    
    return text

def analyze_cv(cv_path, job_description, job_requirements):
    """
    Analyser un CV par rapport à une description de poste en utilisant l'API Vision d'OpenAI
    
    Args:
        cv_path: Chemin vers le fichier PDF du CV
        job_description: Description du poste
        job_requirements: Exigences du poste
        
    Returns:
        tuple: (analyse détaillée, score de correspondance)
    """
    # Vérifier que la clé API est disponible
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("La clé API OpenAI n'est pas configurée. Veuillez définir la variable d'environnement OPENAI_API_KEY.")
    
    # Convertir le PDF en images
    pdf_images = convert_pdf_to_images(cv_path)
    
    if not pdf_images:
        # Si la conversion échoue, revenir à l'extraction de texte
        print("Conversion du PDF en images échouée, retour à l'extraction de texte")
        cv_text = extract_text_from_pdf(cv_path)
        if not cv_text or cv_text.startswith("Erreur"):
            return "Impossible d'analyser le CV. Veuillez vérifier le format du fichier.", 0
            
        # Utiliser la méthode classique
        return analyze_cv_with_text(cv_text, job_description, job_requirements, api_key)
    
    # Limiter le nombre d'images à traiter pour ne pas dépasser les limites de l'API
    max_pages = min(5, len(pdf_images))  # Limiter à 5 pages maximum
    
    try:
        # Utiliser les requêtes HTTP directes plutôt que le client OpenAI
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # Construire le message avec les images du CV
        messages = [
            {"role": "system", "content": "Vous êtes un expert RH spécialisé dans l'analyse de CV."}
        ]
        
        # Premier message contenant le contexte et la première image
        content = [
            {"type": "text", "text": f"""
            Vous êtes un expert RH chargé d'analyser la correspondance entre un CV et une offre d'emploi.
            
            Description du poste:
            {job_description}
            
            Exigences du poste:
            {job_requirements}
            
            Voici le CV du candidat (les pages suivent). Analysez-le en détail.
            """}
        ]
        
        # Ajouter les images du CV
        for i, image in enumerate(pdf_images[:max_pages]):
            base64_image = encode_image_to_base64(image)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
            
            # Si on a plusieurs pages, les envoyer comme des messages séparés
            if i < max_pages - 1 and i > 0 and i % 2 == 1:
                messages.append({"role": "user", "content": content})
                content = [{"type": "text", "text": f"Suite du CV (page {i+2})"}]
        
        # Ajouter le dernier message s'il reste du contenu
        if content:
            messages.append({"role": "user", "content": content})
        
        # Ajouter un message final demandant l'analyse
        messages.append({"role": "user", "content": """
        Après avoir analysé ce CV par rapport à la description du poste et aux exigences, veuillez fournir:
        1. Une évaluation générale de l'adéquation entre le profil du candidat et le poste (sur 100)
        2. Les points forts du candidat par rapport au poste
        3. Les compétences manquantes ou à développer
        4. Une recommandation (inviter à un entretien, demander plus d'informations, ou refuser poliment)
        
        Format de réponse souhaité:
        SCORE: [score numérique sur 100]
        
        ANALYSE:
        [votre analyse détaillée]
        """})
        
        # Préparer la payload pour l'API
        payload = {
            "model": "gpt-4o",  # Utilisation du nouveau modèle qui remplace gpt-4-vision-preview
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.2
        }
        
        # Appel direct à l'API OpenAI avec désactivation de la vérification SSL
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            verify=False  # Désactiver la vérification SSL
        )
        
        # Vérifier la réponse
        if response.status_code != 200:
            raise Exception(f"Erreur API OpenAI: {response.status_code} - {response.text}")
            
        # Extraire la réponse
        response_data = response.json()
        analysis = response_data["choices"][0]["message"]["content"].strip()
        
        # Extraire le score
        score = 0
        if "SCORE:" in analysis:
            try:
                score_line = [line for line in analysis.split('\n') if "SCORE:" in line][0]
                score_text = score_line.split("SCORE:")[1].strip().split()[0]
                
                # Extraire uniquement les chiffres avant tout caractère non numérique
                import re
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    score = float(score_match.group(1))
                else:
                    score = 0
            except Exception as e:
                print(f"Erreur lors de l'extraction du score: {e}")
                score = 0
        
        return analysis, score
        
    except Exception as e:
        import traceback
        error_message = f"Erreur lors de l'analyse du CV avec l'API Vision: {str(e)}"
        print(error_message)
        traceback.print_exc()
        # En cas d'échec, essayer la méthode classique
        print("Tentative d'analyse avec la méthode classique d'extraction de texte")
        cv_text = extract_text_from_pdf(cv_path)
        return analyze_cv_with_text(cv_text, job_description, job_requirements, api_key)

def analyze_cv_with_text(cv_text, job_description, job_requirements, api_key):
    """
    Méthode de secours qui utilise l'extraction de texte classique
    """
    if not cv_text or cv_text.startswith("Erreur"):
        return cv_text, 0
    
    # Limiter la taille du texte pour éviter de dépasser les limites de l'API
    cv_text = cv_text[:4000]  # Limiter à 4000 caractères
    
    # Préparer le prompt pour l'API
    prompt = f"""
    Vous êtes un expert en ressources humaines chargé d'évaluer l'adéquation entre un CV et une offre d'emploi.
    
    Description du poste:
    {job_description}
    
    Exigences du poste:
    {job_requirements}
    
    CV du candidat:
    {cv_text}
    
    Veuillez analyser ce CV par rapport à la description du poste et aux exigences, puis fournir:
    1. Une évaluation générale de l'adéquation entre le profil du candidat et le poste (sur 100)
    2. Les points forts du candidat par rapport au poste
    3. Les compétences manquantes ou à développer
    4. Une recommandation (inviter à un entretien, demander plus d'informations, ou refuser poliment)
    
    Format de réponse souhaité:
    SCORE: [score numérique sur 100]
    
    ANALYSE:
    [votre analyse détaillée]
    """
    
    try:
        # Utiliser les requêtes HTTP directes
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Préparer la payload pour l'API
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Vous êtes un expert RH spécialisé dans l'analyse de CV."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.5
        }
        
        # Appel direct à l'API OpenAI avec désactivation de la vérification SSL
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            verify=False  # Désactiver la vérification SSL
        )
        
        # Vérifier la réponse
        if response.status_code != 200:
            raise Exception(f"Erreur API OpenAI: {response.status_code} - {response.text}")
            
        # Extraire la réponse
        response_data = response.json()
        analysis = response_data["choices"][0]["message"]["content"].strip()
        
        # Extraire le score
        score = 0
        if "SCORE:" in analysis:
            try:
                score_line = [line for line in analysis.split('\n') if "SCORE:" in line][0]
                score_text = score_line.split("SCORE:")[1].strip().split()[0]
                
                # Extraire uniquement les chiffres avant tout caractère non numérique
                import re
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    score = float(score_match.group(1))
                else:
                    score = 0
            except Exception as e:
                print(f"Erreur lors de l'extraction du score dans analyze_cv_with_text: {e}")
                score = 0
        
        return analysis, score
        
    except Exception as e:
        import traceback
        error_message = f"Erreur lors de l'analyse du CV avec l'API OpenAI: {str(e)}"
        print(error_message)
        traceback.print_exc()
        return error_message, 0
