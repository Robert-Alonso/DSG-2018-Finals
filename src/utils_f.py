import re
import pandas as pd
import numpy as np

################### FEATURES ###################

def duration_feature(session_features, train_tracking):
    train_tracking = duration_to_seconds(train_tracking)
    durations = train_tracking.groupby('sid').duration.max().reset_index()
    durations.columns = ['sid', 'TOTAL_DURATION']
    session_features = pd.merge(session_features, durations, on='sid', how='left')
    return session_features

def purchased_products(session_features, train_tracking):
    quants = train_tracking[(train_tracking.type=='PURCHASE_PRODUCT_UNKNOWN_ORIGIN') | (train_tracking.type=='PURCHASE_PRODUCT_SHOW_CASE')\
                   | (train_tracking.type=='PURCHASE_PRODUCT_PA') | (train_tracking.type=='PURCHASE_PRODUCT_LR')\
                   | (train_tracking.type=='PURCHASE_PRODUCT_LP') | (train_tracking.type=='PURCHASE_PRODUCT_CAROUSEL')].groupby('sid').quantity.sum().reset_index()
    quants.columns = ['sid', 'PURCHASED_PRODUCTS']
    session_features = pd.merge(session_features, quants, on='sid', how='left')
    return session_features

def watched_category(session_features, train_tracking, product):
    print('Loading pages')
    train_tracking = add_page(train_tracking)
    print('Loading categories')
    product = simplify_categories(product)
    print('Loading catmap')
    catmap = dict(zip(product.product_id, product.cat1))
    
    prods = fast_convert_jsonproducts(train_tracking[pd.notnull(train_tracking.products)].copy(), 'products')
    prods['prod_counter'] = prods.product_list.apply(cat_counter)
    session_prods = prods.groupby('sid').prod_counter.agg(merge_counters).reset_index()
    
    def top_cat(x):
        evaluation = Counter(x)
        return evaluation.most_common(1)[0][0]
    session_prods['top_cat'] = session_prods.prod_counter.apply(top_cat)
    
    session_cat = session_prods[['sid', 'top_cat']].copy()
    session_cat.columns = ['sid', 'WATCHED_CATEGORY']
    session_features = pd.merge(session_features, session_cat, on='sid', how='left')
    
    return session_features

################### OTHERS #####################    

# Convertir duration a total de segundos
def duration_to_seconds(train_tracking):
    train_tracking.duration = pd.to_timedelta(train_tracking.duration).dt.total_seconds()
    return train_tracking

def add_page(train_tracking):
    def extract_page(x):
        pages_types = ['_LR', '_PA', '_LP', '_CAROUSEL', '_SHOW_CASE']
        pages = ['CAROUSEL', 'PA', 'SEARCH', 'SHOW_CASE', 'LIST_PRODUCT']
        pages_map = [['PURCHASE_PRODUCT_UNKNOW_ORIGIN', 'UNKNOWN']]
        for pages_type in pages_types:
            if x.endswith(pages_type):
                return x[-len(pages_type)+1:]
        for page in pages:
            if x == page:
                return x
        for page_map in pages_map:
            if x == page_map[0]:
                return page_map[1]
        return '::' + x
    train_tracking['page'] = train_tracking.type.apply(extract_page)

def simplify_categories(train_tracking, product):
    counter1 = product.groupby('category_product_id_level1').size()
    counter1dict = counter1.to_dict()
    mapcat = {}
    for idx in counter1dict:
        if counter1dict[idx] > 10:
            mapcat[idx] = idx
        else:
            mapcat[idx] = 10e7
    product['cat1'] = product.category_product_id_level1.apply(lambda x: mapcat[x])

def add_page(train_tracking):
    def extract_page(x):
        pages_types = ['_LR', '_PA', '_LP', '_CAROUSEL', '_SHOW_CASE']
        pages = ['CAROUSEL', 'PA', 'SEARCH', 'SHOW_CASE', 'LIST_PRODUCT']
        pages_map = [['PURCHASE_PRODUCT_UNKNOW_ORIGIN', 'UNKNOWN']]
        for pages_type in pages_types:
            if x.endswith(pages_type):
                return x[-len(pages_type)+1:]
        for page in pages:
            if x == page:
                return x
        for page_map in pages_map:
            if x == page_map[0]:
                return page_map[1]
        return '::' + x
    train_tracking['page'] = train_tracking.type.apply(extract_page)
    return train_tracking

def simplify_categories(product):
    counter1 = product.groupby('category_product_id_level1').size()
    counter1dict = counter1.to_dict()
    mapcat = {}
    for idx in counter1dict:
        if counter1dict[idx] > 10:
            mapcat[idx] = idx
        else:
            mapcat[idx] = 10e7
    product['cat1'] = product.category_product_id_level1.apply(lambda x: mapcat[x])
    return product

def fast_convert_jsonproducts(train_tracking, column):
    prog = re.compile("'sku':\ *'([a-zA-Z0-9\+\=\/]+)'")
    train_tracking['product_list'] = train_tracking[column].apply(lambda val: re.findall(prog, val))
    return train_tracking

def cat_counter(prodlist):
    global product
    try:
        counter = {}
        for prod in prodlist:
            if not prod in catmap:
                # print('CANT FIND ' + prod['sku'])
                # print(prodlist)
                cat = 10e7
            else:
                cat = int(catmap[prod])
            if cat in counter:
                counter[cat] = counter[cat] + 1
            else:
                counter[cat] = 1
        return counter
    except:
        print(prodlist)
        print("ERROR")
        return {}

def merge_counters(counters):
    merged = {}
    for counter in counters:
        for key in counter:
            if key in merged:
                merged[key] = merged[key] + counter[key]
            else:
                merged[key] = counter[key]
        # merged = {**merged, **counter}
    return merged