import logging
import json
import azure.functions as func
import os 
import pysolr
from __app__.shared_code import settings as config
from __app__.shared_code import helper
solr_unstructure_data=config.solr_unstructure_data

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('postSalesInformation function processing a request.')
        result=[]
        req_body = req.get_json()
        found_data = get_sales_data_details(req_body[0])
        result = json.dumps(found_data)
    except Exception as e:
        logging.error(str(e))
    return func.HttpResponse(result,mimetype="application/json")

def get_sales_data_details(req_body):
    try:
        category=["SAP-BW"]
        material_level_data=req_body.get("Mat_Level")
        all_details_json,spec_list,material_list=helper.construct_common_level_json(req_body)
        sale_info_query=helper.unstructure_template(all_details_json,category)
        params={"fl":config.unstructure_column_str}
        result,result_df=helper.get_data_from_core(solr_unstructure_data,sale_info_query,params)
        sales_list=[]
        sales_kg=0
        sales_org=[]
        region=[]
        material_flag=''
        for mat_id in material_list:
            for data in result: 
                material_number=data.get("PRODUCT")
                if material_number==mat_id:
                    material_flag='s'
                    result_spec=data.get("SPEC_ID")  
                    spec_id=helper.finding_spec_details(spec_list,result_spec)
                    data_extract=json.loads(data.get("DATA_EXTRACT"))
                    sales_org.append(data_extract.get("Sales Organization"))
                    sales_kg=sales_kg+int(data_extract.get("SALES KG"))
                    region.append(data_extract.get("Sold-to Customer Country"))
                    material_number=data.get("PRODUCT")
            if material_flag=='s':
                desc=[]
                bdt=[]       
                for item in material_level_data:
                    if item.get("material_Number")==mat_id:
                        desc.append(item.get("description"))
                        bdt.append(item.get("bdt"))
                sales_json={
                    "material_number":mat_id,
                    "material_description":(config.comma_delimiter).join(list(set(desc))),
                    "basic_data":(config.comma_delimiter).join(list(set(bdt))),
                    "sales_Org":(config.comma_delimiter).join(list(set(sales_org))),
                    "past_Sales":str(sales_kg)+" Kg",
                    "spec_id":spec_id,
                    "region_sold":(config.comma_delimiter).join(list(set(region)))
                    }
                sales_list.append(sales_json) 
                sales_json={}
                material_flag=''
                sales_kg=0
                sales_org=[]
                region=[]
        result_data={"saleDataProducts":sales_list}
        return [result_data]
    except Exception as e:
        print(e)
        return []
