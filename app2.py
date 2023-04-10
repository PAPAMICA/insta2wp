import os
import requests
import json

# Informations d'authentification Wordpress
wp_url = os.environ.get('WORDPRESS_URL')
wp_username = os.environ.get('WORDPRESS_USERNAME')
wp_password = os.environ.get('WORDPRESS_PASSWORD')

# Informations d'authentification Instagram
instagram_token = os.environ.get('INSTAGRAM_TOKEN')

# Récupération des dernières publications Instagram
response = requests.get(f'https://graph.instagram.com/me/media?fields=id,media_type,media_url,caption&access_token={instagram_token}')
ig_data = json.loads(response.text)

print(ig_data)

response = requests.get(f'{wp_url}/wp-json/wp/v2/posts')
posts = json.loads(response.text)

for post in posts:
    print(post['title']['rendered'])
    print(post['slug'])

# Boucle pour parcourir les publications et créer des articles sur Wordpress
for post in ig_data['data']:
    # Extraction des informations de publication
    post_id = post['id']
    post_type = post['media_type']
    post_url = post['media_url']
    post_caption = post['caption']
    
    # Vérification de l'existence de l'article sur Wordpress
    response = requests.get(f'{wp_url}/wp-json/wp/v2/posts?slug={post_id}')
    existing_post = json.loads(response.text)
    
    if len(existing_post) > 0:
        print(f"L'article pour la publication Instagram {post_caption if post_caption else f'Instagram post {post_id}'} existe déjà sur le site.")
        continue
    
    # Téléchargement de l'image
    image_response = requests.get(post_url)
    if image_response.status_code != 200:
        print(f"Une erreur est survenue lors du téléchargement de l'image : {image_response.text}")
        continue
    
    # Importation de l'image dans la bibliothèque Wordpress
    files = {'file': (f'{post_id}.jpg', image_response.content)}
    headers = {'Content-Type': 'application/json'}
    auth = requests.auth.HTTPBasicAuth(wp_username, wp_password)
    media_response = requests.post(f'{wp_url}/wp-json/wp/v2/media', headers=headers, files=files, auth=auth)
    if media_response.status_code == 201:
        print(f"L'image pour la publication Instagram {post_caption if post_caption else f'Instagram post {post_id}'} a été importée avec succès dans la bibliothèque !")
        # Récupération de l'URL de l'image importée
        media_url = json.loads(media_response.text)['guid']['rendered']
    else:
        print(f"Une erreur est survenue lors de l'importation de l'image : {media_response.text}")
        continue
    
    # Création de l'article sur Wordpress
    wp_post_data = {
        'title': {'raw': post_caption if post_caption else f'Instagram post {post_id}'},
        'content': {'raw': f'<img src="{media_url}" alt="{post_caption}" />'},
        'slug': post_id,
        'status': 'publish',
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
