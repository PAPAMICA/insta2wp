import os
import glob
import requests
import json
import base64
import re
import time
from datetime import datetime


# Informations d'authentification WooCommerce
wc_url = os.environ.get('WOOCOMMERCE_URL')
wc_consumer_key = os.environ.get('WOOCOMMERCE_CONSUMER_KEY')
wc_consumer_secret = os.environ.get('WOOCOMMERCE_CONSUMER_SECRET')
wp_url = os.environ.get('WORDPRESS_URL')
wp_username = os.environ.get('WORDPRESS_USERNAME')
wp_password = os.environ.get('WORDPRESS_PASSWORD')
discord_webhook = os.environ.get('DISCORD_WEBHOOK')

# Informations d'authentification Instagram
instagram_token = os.environ.get('INSTAGRAM_TOKEN')

# Identification WordPress
credentials = wp_username + ':' + wp_password
token = base64.b64encode(credentials.encode())
header_json = {'Authorization': 'Basic ' + token.decode('utf-8')}


# Envoi des images sur WordPress
def wp_upload_img(i,imd_id,img_url,post_title,post_id):
    if imd_id != '':
        response = requests.get(f"https://graph.instagram.com/{imd_id}?fields=id,media_type,media_url&access_token={instagram_token}")
        ig_data = json.loads(response.text)
        image_response = requests.get(ig_data['media_url'])
    else:
        #print(img_url[0])
        image_response = requests.get(img_url[0])

    if image_response.status_code == 200:
        # Enregistrement de l'image localement
        img = f'{post_id}_{i}.jpg'
        with open(f'{post_id}_{i}.jpg', 'wb') as f:
            f.write(image_response.content)
            
        # Upload de l'image sur Wordpress
        media = {'file': open(f'{post_id}_{i}.jpg',"rb"),'title': f"{post_title if post_title else f'Instagram post {post_id}'}_{i}"}
        img_response = requests.post(f'{wp_url}/wp-json/wp/v2/media', headers=header_json, files = media)

        if img_response.status_code == 201:
            print(f"L\'image de {post_title if post_title else f'Instagram post {post_id}'}_{i} a été uploadée avec succès sur Wordpress !")
            img_data = json.loads(img_response.text)
        else:
            print(f"Une erreur est survenue lors de l\'upload de l\'image de {post_title if post_title else f'Instagram post {post_id}'}_{i} sur Wordpress")
    else:
        print(f"Impossible de récupérer l\'image de {post_title if post_title else f'Instagram post {post_id}'}_{i} depuis l\'URL spécifiée")

    # Suppression de l'image localement
    #os.remove(f'{post_id}.jpg')
    return img

# Envoi d'une notification sur Discord
def send_discord(notif):
    webhook_url = discord_webhook

    message = {
        "content": notif
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(webhook_url, data=json.dumps(message), headers=headers)

    if response.status_code == 204:
        print("Le message a été envoyé avec succès à Discord !")
    else:
        print(f"Une erreur est survenue : {response.text}")


# Récupération des dernières publications Instagram
response = requests.get(f'https://graph.instagram.com/me/media?fields=id,media_type,media_url,timestamp,caption&access_token={instagram_token}')
ig_data = json.loads(response.text)

# Récupération du timestamp actuel
current_timestamp = int(time.time())

#print(ig_data)

# Boucle pour parcourir les publications et créer des produits sur WooCommerce
recent_posts = [post for post in ig_data['data'] if current_timestamp - datetime.fromisoformat(post['timestamp'].replace('+0000', '')).timestamp() < 10800]

#print(recent_posts)

for post in recent_posts:
    #print(post)
    post_id = post['id']
    try:
        # Extraction des informations de publication
        post_type = post['media_type']
        post_url = post['media_url']
        post_cat = post['caption'].split('#', 1)[-1].split()[0]
        post_title = post['caption'].split('\n')[0]
        post_desc = post['caption'].split('\n')[1]
        #post_price = post['caption'].split('\n')[2]
        match = re.search(r'\d+', post['caption'].split('\n')[2])
        if match:
            post_price = str(match.group())
        else:
            print("Aucun prix trouvé")
            post_price = ''
        img_list = []
        

        # Vérification de l'existance du produit
        response = requests.get(f'{wc_url}/wp-json/wc/v3/products?slug={post_id}', auth=(wc_consumer_key, wc_consumer_secret))
        existing_products = json.loads(response.text)

        if existing_products:
            print(f"Le produit {post_title} existe déjà !")
        else:
            # Téléchargement de l'image depuis Instagram
            if post['media_type'] == "CAROUSEL_ALBUM":
                #print(post)
                carousel_id = post['id']
                response = requests.get(f'https://graph.instagram.com/{carousel_id}/children?access_token={instagram_token}')
                children_data = json.loads(response.text)
                #print(children_data)
                i=0
                for image in children_data['data']:
                    #print(image['id'])
                    i=i+1
                    img = wp_upload_img(i,image['id'],'',post_title,post_id)
                    img_list.append({"src": f'https://nevermind.papamica.dev/wp-content/uploads/{img}'})
            
            else:
                image_url = [post['media_url']]
                i=1
                img = wp_upload_img(i,'',image_url,post_title,post_id)
                img_list.append({"src": f'https://nevermind.papamica.dev/wp-content/uploads/{img}'})

            # Récupérer l'ID de la catégorie
            response = requests.get(f"{wc_url}/wp-json/wc/v3/products/categories?slug={post_cat}", auth=(wc_consumer_key, wc_consumer_secret))
            category_id = response.json()[0]['id']
            category_parent_id = response.json()[0]['parent']
            if not category_id:
                category_id = 0
            cat_list =[]
            cat_list.append({"id": category_id})
            if category_parent_id != "0":
                cat_list.append({"id": category_parent_id})
            
            # Création du produit sur WooCommerce
            wc_product_data = {
                'name': post_title if post_title else f'Instagram post {post_id}',
                'description': post_desc,
                'slug': post_id,
                'short_description': '',
                'type': 'simple',
                'regular_price': post_price,
                'categories': cat_list,
                "images": img_list
            }
            response = requests.post(f'{wc_url}/wp-json/wc/v3/products', auth=(wc_consumer_key, wc_consumer_secret), json=wc_product_data)
            #print(response.text)

            if response.status_code == 201:
                print(f"Le produit {post_title if post_title else f'Instagram post {post_id}'} a été créé avec succès sur WooCommerce ! ({i} photos)")
                send_discord(f" ✅ - Le produit {post_title if post_title else f'Instagram post {post_id}'} a été créé avec succès sur WooCommerce ! ({i} photos)")
            else:
                print(f"Une erreur est survenue lors de la création du produit {post_title if post_title else f'Instagram post {post_id}'} sur WooCommerce")
                send_discord(f" ❌ - Une erreur est survenue lors de la création du produit {post_title if post_title else f'Instagram post {post_id}'} sur WooCommerce")
            
    except:
        print(f"Le post Instagram {post_id} n'est pas formatté correctement !")
        send_discord(f" ⚠️ - Le post Instagram {post_id} n'est pas formatté correctement !")
        continue

# Suppression de l'image localement
for file in glob.glob("*.jpg"):
    os.remove(file)