#uvicorn main:app --reload
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="/code")

@app.get("/")
def form_post(request: Request):
    return templates.TemplateResponse('portfolio.html', context={'request': request})

@app.get("/new")
def form_post(request: Request):
    return templates.TemplateResponse('new.html', context={'request': request})
