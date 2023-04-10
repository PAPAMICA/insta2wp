import os
import requests
import json
import base64

# Informations d'authentification Wordpress
wp_url = os.environ.get('WORDPRESS_URL')
wp_username = os.environ.get('WORDPRESS_USERNAME')
wp_password = os.environ.get('WORDPRESS_PASSWORD')

# Informations d'authentification Instagram
instagram_token = os.environ.get('INSTAGRAM_TOKEN')

# Récupération des dernières publications Instagram
response = requests.get(f'https://graph.instagram.com/me/media?fields=id,media_type,media_url,caption&access_token={instagram_token}')
ig_data = json.loads(response.text)

credentials = wp_username + ':' + wp_password
token = base64.b64encode(credentials.encode())
header_json = {'Authorization': 'Basic ' + token.decode('utf-8')}

# Boucle pour parcourir les publications et créer des articles sur Wordpress
for post in ig_data['data']:
    # Extraction des informations de publication
    post_id = post['id']
    post_type = post['media_type']
    post_url = post['media_url']
    post_caption = post['caption']
    
    # Vérification de l'existance du post
    response = requests.get(f'{wp_url}/wp-json/wp/v2/posts?slug={post_id}')
    existing_posts = json.loads(response.text)

    if existing_posts:
        print(f"L'article avec le slug {post_caption} existe déjà !")
    else:
        # Téléchargement de l'image depuis Instagram
        image_response = requests.get(post_url)

        if image_response.status_code == 200:
            # Enregistrement de l'image localement
            with open(f'{post_id}.jpg', 'wb') as f:
                f.write(image_response.content)
                
            # Upload de l'image sur Wordpress
            media = {'file': open(f'{post_id}.jpg',"rb"),'title': f"{post_caption if post_caption else f'Instagram post {post_id}'}"}
            img_response = requests.post(f'{wp_url}/wp-json/wp/v2/media', headers=header_json, files = media)

            if img_response.status_code == 201:
                print(f"L\'image de {post_caption if post_caption else f'Instagram post {post_id}'} a été uploadée avec succès sur Wordpress !")
                img_data = json.loads(img_response.text)
            else:
                print(f"Une erreur est survenue lors de l\'upload de l\'image de {post_caption if post_caption else f'Instagram post {post_id}'} sur Wordpress")
        else:
            print(f"Impossible de récupérer l\'image de {post_caption if post_caption else f'Instagram post {post_id}'} depuis l\'URL spécifiée")

        # Création de l'article sur Wordpress
        wp_post_data = {
            'title': post_caption if post_caption else f'Instagram post {post_id}',
            'content': f'<img src="{post_url}" alt="{post_caption}" />',
            'slug': f'{post_id}',
            'featured_media': img_data['id'],
            'status': 'publish'
            #'categories': [1]  # ID de la catégorie à laquelle ajouter l'article
        }
        headers = {'Content-Type': 'application/json'}
        auth = requests.auth.HTTPBasicAuth(wp_username, wp_password)
        response = requests.post(f'{wp_url}/wp-json/wp/v2/posts', headers=headers, json=wp_post_data, auth=auth)
        
        # Vérification de la réponse du serveur
        if response.status_code == 201:
            print(f"L'article pour la publication Instagram {post_caption if post_caption else f'Instagram post {post_id}'} a été créé avec succès !")
        else:
            print(f"Une erreur est survenue lors de la publication de l'article : {response.text}")
