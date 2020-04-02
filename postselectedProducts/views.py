import json
import re
import pandas as pd
import pysolr
from __app__.shared_code import settings as config
from __app__.shared_code import helper
solr_product=config.solr_product
solr_notification_status=config.solr_notification_status
solr_unstructure_data=config.solr_unstructure_data
solr_document_variant=config.solr_document_variant
junk_column=config.junk_column
product_column=config.product_column
product_nam_category=config.product_nam_category
product_rspec_category = config.product_rspec_category
product_namsyn_category = config.product_namsyn_category
material_number_category = config.material_number_category
material_bdt_category = config.material_bdt_category
cas_number_category = config.cas_number_category
cas_pspec_category = config.cas_pspec_category
cas_chemical_category = config.cas_chemical_category
category_with_key=config.category_with_key
category_type = config.category_type
search_category = config.search_category
selected_categories=config.selected_categories
querying_solr_data=helper.querying_solr_data
product_level_creation=helper.product_level_creation
solr_product_params=config.solr_product_params
replace_character_for_querying=helper.replace_character_for_querying

def selected_products(data_json):
    try:
        searched_product_list=[]
        count=0
        params=solr_product_params
        product_count=0
        material_count=0
        cas_count=0
        column_add=[]
        product_level_flag=''
        material_level_flag=''
        cas_level_flag=''
        add_df=pd.DataFrame()
        material_df=pd.DataFrame()
        cas_df=pd.DataFrame()
        prod_df=pd.DataFrame()
        result={}
        if len(data_json)<=2:
            for item in data_json:
                search_value = item.get("name")
                search_value_split = search_value.split(" | ")
                search_column = item.get("type")
                search_key = item.get("key")
                search_column_split = search_column.split(" | ")
                search_group = item.get("group").split("(")
                search_group = search_group[0].strip()
                column_add.append(search_column)
                count+=1
                if search_group == "PRODUCT-LEVEL":
                    product_level_flag = 's'
                    product_count = count
                    product_rspec = search_value_split[search_column_split.index("REAL-SPECID")]
                    product_name = search_value_split[search_column_split.index("NAM PROD")]
                    product_synonyms = search_value_split[search_column_split.index("SYNONYMS")]
                    product_level_json={"spec_Id":product_rspec,"namprod":product_name,"synonyms":product_synonyms}                     
                if search_group == "MATERIAL-LEVEL":
                    material_level_flag = 's'
                    material_count = count
                    material_number = search_value_split[search_column_split.index("MATERIAL NUMBER")]
                    material_bdt = search_value_split[search_column_split.index("BDT")]
                    material_description = search_value_split[search_column_split.index("DESCRIPTION")]
                    material_level_json = {"material_Number":material_number,"bdt":material_bdt,"description":material_description}
                if search_group == "CAS-LEVEL":
                    cas_level_flag = 's'
                    cas_count = count
                    cas_pspec = search_value_split[search_column_split.index("PURE-SPECID")]  
                    cas_number = search_value_split[search_column_split.index("CAS NUMBER")]
                    cas_chemical = search_value_split[search_column_split.index("CHEMICAL-NAME")]  
                    cas_level_json = {"pure_spec":cas_pspec,"cas_number":cas_number,"chemical_Name":cas_chemical}
                                           
            if product_level_flag=='s' and product_count==1:
                real_spec_list=[product_rspec]
                if material_level_flag=='' and cas_level_flag=='':                     
                    #to find material level details
                    material_df=finding_material_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(material_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                    #to find cas level details
                    cas_df,spec_rel_list=finding_cas_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(cas_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")
                    properties=basic_properties("product_level","","",product_level_json,material_df,cas_df,spec_rel_list,real_spec_list)

                elif material_level_flag=='s' and material_count==2 and cas_level_flag=='':
                    #to find cas level details
                    cas_df,spec_rel_list=finding_cas_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(cas_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")
                    properties=basic_properties("product_level","material_level","",product_level_json,material_level_json,cas_df,spec_rel_list,real_spec_list)

                elif cas_level_flag=='s' and cas_count==2 and material_level_flag=='':
                    #to find material level details
                    material_df=finding_material_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(material_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                    properties=basic_properties("product_level","","cas_level",product_level_json,material_df,cas_level_json,"",real_spec_list)
            
            elif material_level_flag =='s' and material_count==1:
                #finding real spec id
                query=f'TYPE:MATNBR && TEXT1:{material_number}'
                temp_df=querying_solr_data(query,params)
                real_spec_list = list(temp_df["TEXT2"].unique())
                if product_level_flag =='' and cas_level_flag=='':
                    #find product details
                    prod_df=finding_product_details_using_real_specid(real_spec_list,params)           
                    searched_product_list=searched_product_list+product_level_creation(prod_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                    #cas level details
                    cas_df,spec_rel_list=finding_cas_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(cas_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")
                    properties=basic_properties("","material_level","",prod_df,material_level_json,cas_df,spec_rel_list,real_spec_list)

                elif product_level_flag =='s' and product_count ==2 and cas_level_flag=='':
                    real_spec_list = [product_rspec]
                    #cas level details
                    cas_df,spec_rel_list=finding_cas_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(cas_df,cas_number_category,"","","CAS*","CAS-LEVEL","yes")
                    properties=basic_properties("product_level","material_level","",product_level_json,material_level_json,cas_df,spec_rel_list,real_spec_list)  
                elif cas_level_flag=='s' and cas_count==2 and product_level_flag=='':
                    #find product details
                    prod_df=finding_product_details_using_real_specid(real_spec_list,params)           
                    searched_product_list=searched_product_list+product_level_creation(prod_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                          
                    properties=basic_properties("","material_level","cas_level",prod_df,material_level_json,cas_level_json,spec_rel_list,real_spec_list)

            elif cas_level_flag=='s' and cas_count==1:
                #finding real spec id
                query=f'TYPE:SUBIDREL && TEXT1:{cas_pspec}'
                temp_df=querying_solr_data(query,params)
                spec_rel_list=temp_df[["TEXT1","TEXT2"]].values.tolist()
                real_spec_list = list(temp_df["TEXT2"].unique())
                if product_level_flag =='' and material_level_flag=='':
                    #find product details
                    prod_df=finding_product_details_using_real_specid(real_spec_list,params)           
                    #same pure-spec will be act as real-spec
                    query=f'TYPE:NAMPROD && TEXT2:{cas_pspec} && SUBCT:PURE_SUB'
                    pure_real_df=querying_solr_data(query,params)
                    prod_df=pd.concat([prod_df,pure_real_df])
                    searched_product_list=searched_product_list+product_level_creation(prod_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")
                    #to find material level details
                    material_df=finding_material_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(material_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                    properties=basic_properties("","","cas_level",prod_df,material_df,cas_level_json,spec_rel_list,real_spec_list)

                elif product_level_flag =='s' and product_count ==2 and material_level_flag=='':
                    #to find material level details
                    real_spec_list=[product_rspec]
                    material_df=finding_material_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(material_df,material_number_category,"","","MAT*","MATERIAL-LEVEL","yes")
                    properties=basic_properties("product_level","","cas_level",product_level_json,material_df,cas_level_json,spec_rel_list,real_spec_list)

                elif material_level_flag=='s' and material_count==2 and product_level_flag=='':
                    #find product details
                    prod_df=finding_product_details_using_real_specid(real_spec_list,params)
                    searched_product_list=searched_product_list+product_level_creation(prod_df,product_rspec_category,"","","RSPEC*","PRODUCT-LEVEL","yes")                                     
                    properties=basic_properties("","material_level","cas_level",prod_df,material_level_json,cas_level_json,spec_rel_list,real_spec_list)
       
        result["search_List"]=searched_product_list
        result["basic_properties"]=properties
        return result     
    except Exception as e:
        return result

def finding_cas_details_using_real_specid(product_rspec,params):
    product_rspec=" || ".join(product_rspec)
    query=f'TYPE:SUBIDREL && TEXT2:({product_rspec}) && SUBCT:REAL_SUB'
    spec_rel_df=querying_solr_data(query,params) 
    spec_rel_list=spec_rel_df[["TEXT1","TEXT2"]].values.tolist()
    column_value = list(spec_rel_df["TEXT1"].unique())
    spec_query=" || ".join(column_value)
    query=f'TYPE:NUMCAS && SUBCT:PURE_SUB && TEXT2:({spec_query})'
    cas_df=querying_solr_data(query,params)                 
    #real spec will act as pure spec componant
    query=f'TYPE:NUMCAS && TEXT2:({product_rspec})'
    real_pure_spec_df=querying_solr_data(query,params)
    cas_df=pd.concat([cas_df,real_pure_spec_df])
    return cas_df,spec_rel_list

def finding_product_details_using_real_specid(product_rspec,params):
    product_rspec=" || ".join(product_rspec)
    query=f'TYPE:NAMPROD && SUBCT:REAL_SUB && TEXT2:({product_rspec})'
    prod_df=querying_solr_data(query,params)
    return prod_df

def finding_material_details_using_real_specid(product_rspec,params):
    product_rspec=" || ".join(product_rspec)
    query=f'TYPE:MATNBR && TEXT2:({product_rspec})'
    material_df=querying_solr_data(query,params)
    return material_df

def basic_properties(p_flag,m_flag,c_flag,product_info,material_info,cas_info,spec_rel_list=[],real_spec_list=[]):
    result={}
    json_make={}
    json_list=[]
    active_material=0
    if m_flag=="material_level":
        active_material+=1
        material_info["real_Spec_Id"]="".join(real_spec_list)
        result["material_Level"]=[material_info]
    else:
        columns=["TEXT1","TEXT4","TEXT3","TEXT2"]
        material_info=material_info[columns]
        material_info=material_info.drop_duplicates()
        material_info=material_info.fillna("-")
        material_result=material_info.values.tolist()
        for number,desc,bdt,specid in material_result:
            json_make["material_Number"]=number
            json_make["description"]=desc
            desc=desc.strip()
            if len(desc)>0 and desc[0]!="^":
                active_material+=1
            json_make["bdt"]=bdt
            json_make["real_Spec_Id"]=specid
            json_list.append(json_make)
            json_make={}
        result["material_Level"]=json_list
        json_list=[]
    if p_flag=="product_level":
        product_info["no_Active_Material"]=active_material
        result["product_Level"]=[product_info]
    else:
        columns=["TEXT1","TEXT2","TEXT3"]
        product_info=product_info[columns]
        product_info=product_info.drop_duplicates()
        product_info=product_info.fillna("-")
        product_result=product_info.values.tolist()
        for namprod,spec,syn in product_result:
            json_make["real_Spec_Id"]=spec
            json_make["namprod"]=namprod
            json_make["synonyms"]=syn
            json_make["no_Active_Material"]=active_material
            json_list.append(json_make)
            json_make={}
        result["product_Level"]=json_list
        json_list=[]    

    if c_flag=="cas_level":
        cas_info["real_Spec_Id"]=real_spec_list
        result["cas_Level"]=[cas_info]
    else:
        columns=["TEXT2","TEXT1","TEXT3"]
        cas_info=cas_info[columns]
        cas_info=cas_info.drop_duplicates()
        cas_info=cas_info.fillna("-")
        cas_result=cas_info.values.tolist()
        for pspec,cas,chemical in cas_result:
            real_spec_list=[real for pure,real in spec_rel_list if pure==pspec]
            real_spec_list=list(set(real_spec_list))
            json_make["pure_Spec_Id"]=pspec
            json_make["cas_Number"]=cas
            json_make["chemical_Name"]=chemical
            json_make["real_Spec_Id"]=real_spec_list
            json_list.append(json_make)
            json_make={}
        result["cas_Level"]=json_list
        json_list=[]
    return result
