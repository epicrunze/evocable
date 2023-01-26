from fastapi import FastAPI

'''
Main code for the fastapi backend to predict
'''

app = FastAPI()


@app.post("/simple_text/{query}")
async def simple_text(query: str):
    '''
    Args:
        query (str): an in-url string for the sentence to be predicted
    '''

    return {"message": "Hello World"}
