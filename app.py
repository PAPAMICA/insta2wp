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

    post_id = post['id']
    try:
        # Extraction des informations de publication
        post_type = post['media_type']
        post_url = post['media_url']
        post_cat = post['caption'].split('\n')[0].split(' - ')[0]
        post_title = post['caption'].split('\n')[0].split(' - ')[1]
        post_desc = post['caption'].split('\n')[1]
        post_price = post['caption'].split('\n')[2]
    
    
        # Vérification de l'existance du post
        response = requests.get(f'{wp_url}/wp-json/wp/v2/posts?slug={post_id}')
        existing_posts = json.loads(response.text)

        if existing_posts:
            print(f"L'article {post_title} existe déjà !")
        else:
            # Téléchargement de l'image depuis Instagram
            image_response = requests.get(post_url)

            if image_response.status_code == 200:
                # Enregistrement de l'image localement
                with open(f'{post_id}.jpg', 'wb') as f:
                    f.write(image_response.content)
                    
                # Upload de l'image sur Wordpress
                media = {'file': open(f'{post_id}.jpg',"rb"),'title': f"{post_title if post_title else f'Instagram post {post_id}'}"}
                img_response = requests.post(f'{wp_url}/wp-json/wp/v2/media', headers=header_json, files = media)

                if img_response.status_code == 201:
                    print(f"L\'image de {post_title if post_title else f'Instagram post {post_id}'} a été uploadée avec succès sur Wordpress !")
                    img_data = json.loads(img_response.text)
                else:
                    print(f"Une erreur est survenue lors de l\'upload de l\'image de {post_title if post_title else f'Instagram post {post_id}'} sur Wordpress")
            else:
                print(f"Impossible de récupérer l\'image de {post_title if post_title else f'Instagram post {post_id}'} depuis l\'URL spécifiée")

            # Récupérer l'ID de la catégorie

            response = requests.get(f"{wp_url}/wp-json/wp/v2/categories?slug={post_cat}", auth=(wp_username, wp_password))
            category_id = response.json()[0]['id']

            # Création de l'article sur Wordpress
            wp_post_data = {
                'title': post_title if post_title else f'Instagram post {post_id}',
                'content': f'<img src="{wp_url}/wp-content/uploads/{post_id}.jpg" alt="{post_title if post_title else f"Instagram post {post_id}"}"><p>{post_desc}</p></br></br><p>{post_price}</p>',
                'slug': f'{post_id}',
                'featured_media': img_data['id'],
                'categories': category_id,
                'status': 'publish'
            }
            headers = {'Content-Type': 'application/json'}
            auth = requests.auth.HTTPBasicAuth(wp_username, wp_password)
            response = requests.post(f'{wp_url}/wp-json/wp/v2/posts', headers=headers, json=wp_post_data, auth=auth)
            
            # Vérification de la réponse du serveur
            if response.status_code == 201:
                print(f"L'article pour la publication Instagram {post_title if post_title else f'Instagram post {post_id}'} a été créé avec succès !")
            else:
                print(f"Une erreur est survenue lors de la publication de l'article : {response.text}")
            os.remove(f'{post_id}.jpg')
    except:
        print(f"Le post Instagram {post_id} n'est pas formatté correctement !")