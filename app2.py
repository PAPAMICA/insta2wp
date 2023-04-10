import os
import requests
import json
import base64
import re


# Informations d'authentification WooCommerce
wc_url = os.environ.get('WOOCOMMERCE_URL')
wc_consumer_key = os.environ.get('WOOCOMMERCE_CONSUMER_KEY')
wc_consumer_secret = os.environ.get('WOOCOMMERCE_CONSUMER_SECRET')
wp_url = os.environ.get('WORDPRESS_URL')
wp_username = os.environ.get('WORDPRESS_USERNAME')
wp_password = os.environ.get('WORDPRESS_PASSWORD')

# Informations d'authentification Instagram
instagram_token = os.environ.get('INSTAGRAM_TOKEN')

# Récupération des dernières publications Instagram
response = requests.get(f'https://graph.instagram.com/me/media?fields=id,media_type,media_url,caption&access_token={instagram_token}')
ig_data = json.loads(response.text)

#print(ig_data)

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

credentials = wp_username + ':' + wp_password
token = base64.b64encode(credentials.encode())
header_json = {'Authorization': 'Basic ' + token.decode('utf-8')}

# Boucle pour parcourir les publications et créer des produits sur WooCommerce
for post in ig_data['data']:

    post_id = post['id']
    try:
        # Extraction des informations de publication
        post_type = post['media_type']
        post_url = post['media_url']
        post_cat = post['caption'].split('\n')[0].split(' - ')[0]
        post_title = post['caption'].split('\n')[0].split(' - ')[1]
        post_desc = post['caption'].split('\n')[1]
        #post_price = post['caption'].split('\n')[2]
        match = re.search(r'\d+', post['caption'].split('\n')[2])
        if match:
            post_price = str(match.group())
        else:
            print("Aucun prix trouvé")
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
                i=0
                img = wp_upload_img(i,'',image_url,post_title,post_id)
                img_list.append({"src": f'https://nevermind.papamica.dev/wp-content/uploads/{img}'})

            # Récupérer l'ID de la catégorie

            #response = requests.get(f"{wc_url}/wp-json/wc/v3/products/categories?slug={post_cat}", auth=(wc_consumer_key, wc_consumer_secret))
            #category_id = response.json()[0]['id']
            
            # Création du produit sur WooCommerce
            wc_product_data = {
                'name': post_title if post_title else f'Instagram post {post_id}',
                'description': post_desc,
                'slug': post_id,
                'short_description': '',
                'type': 'simple',
                'regular_price': post_price,
                #'categories': [{'id': category_id}],
                "images": img_list
            }
            response = requests.post(f'{wc_url}/wp-json/wc/v3/products', auth=(wc_consumer_key, wc_consumer_secret), json=wc_product_data)
            #print(response.text)

            if response.status_code == 201:
                print(f"Le produit {post_title if post_title else f'Instagram post {post_id}'} a été créé avec succès sur WooCommerce !")
            else:
                print(f"Une erreur est survenue lors de la création du produit {post_title if post_title else f'Instagram post {post_id}'} sur WooCommerce")
            
    except:
        print(f"Le post Instagram {post_id} n'est pas formatté correctement !")
        continue

# Suppression de l'image localement
#os.remove(f'*.jpg')