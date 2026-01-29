from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi import status
from fastapi import Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pymysql
from argon2 import PasswordHasher

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(SessionMiddleware, secret_key="Li4B5pyEBaH2Ru5x8PdkjMkYJGNM1ysZb0aKVr16ttQ")

@app.get("/")
def index(request: Request):

    if request.session.get("adm"):
        return RedirectResponse(
            url="/administracao"
        )
    
    if request.session.get("usuario"):
        return RedirectResponse(
            url="/dashboard"
        )
    

    return FileResponse('templates/index.html')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

def connectar_ao_banco():
    connector = pymysql.connect(
        host="crossover.proxy.rlwy.net",
        user="root",
        password="LPwOrhrSuyQVxVjGIOTUlUloughdfEBB",
        database="railway",
        port=40562
    )

    # connector = pymysql.connect(
    #     host="localhost",
    #     user="root",
    #     password="",
    #     database="future_magnorum_empresas"
    # )

    return connector

def criptografar(senha):
    ph = PasswordHasher()
    hash = ph.hash(senha)
    return hash
    

def altenticar(login, senha, request):
    # Conexão com o banco

    connector = connectar_ao_banco()

    # Puxa informaões do banco

    with connector.cursor() as cursor:

        sql = "SELECT * FROM users WHERE login = %s"
        cursor.execute(sql, (login))
        resultado = cursor.fetchall()

        # Valida senha se o login for existente

        if resultado:
            ph = PasswordHasher()
            hash = resultado[0][3]
            try:
                acesso = ph.verify(hash, senha)
            except:
                acesso = False

            if acesso:

                # Salva na sessão do usuário 

                request.session["usuario"] = resultado[0]

                return True
            
        # Reseta a session se falhar na autenticação

        request.session.clear()
        return False
    
    connector.close()

@app.post('/auth')

async def auth(
    request: Request,
    login: str = Form(...),
    senha: str = Form(...)
):
    altenticacao = altenticar(login, senha, request)

    if altenticacao:
        nivel = request.session.get("usuario")[5]

        if nivel == 0:
            request.session["adm"] = request.session.get("usuario")

            response = RedirectResponse(
                url="/administracao",
                status_code=status.HTTP_303_SEE_OTHER
            )
        else:
            response = RedirectResponse(
                url="/dashboard",
                status_code=status.HTTP_303_SEE_OTHER
            )

        return response
    else:
        return RedirectResponse(
            url="/?erro=1",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
templates = Jinja2Templates(directory="templates")

@app.get("/dashboard")

async def dashboard(request: Request):
    # Pega as informações de sessão existentes

    user = request.session.get("usuario")

    # Volta o user para o index se não tiver informações de login

    if not request.session.get("usuario"):
        return RedirectResponse(url="/", status_code=303)
    
    # pega as informações da suas empresa cadastradas

    id_das_empresas = [int(i) for i in user[4].split(",")]

    connector = connectar_ao_banco()

    with connector.cursor() as cursor:
        placeholders = ", ".join(["%s"] * len(id_das_empresas))
        sql = f"SELECT * FROM empresas WHERE id IN ({placeholders})"
        cursor.execute(sql, (id_das_empresas))
        resultado = cursor.fetchall()

    connector.close()

    empresas = []

    # Tranforma as informações do banco em dict

    for i in resultado:
        empresas.append({
            "nome_da_empresa": i[1],
            "email_da_empresa": i[2],
            "senha_da_empresa": i[3],
            "dominio_da_empresa": i[4],
            "senha_do_dominio_da_empresa": i[5]
        })

    # Edita o html para as info do usuario

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "nome": user[1], "empresas": empresas}
    )

@app.get("/logout")
# Sair da conta

async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/administracao")

async def administracao(request: Request):
    if not request.session.get("adm"):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    
    connector = connectar_ao_banco()

    # Pega todas as empresas cadastradas ao banco
    with connector.cursor() as cursor:
        sql = "SELECT * FROM empresas"
        cursor.execute(sql)
        resultado_empresas = cursor.fetchall()

        sql = "SELECT * FROM users"
        cursor.execute(sql)
        resultado_users = cursor.fetchall()
    connector.close()

    empresas = []

    for i in resultado_empresas:
        empresas.append({
            "id_da_empresa": i[0],
            "nome_da_empresa": i[1],
            "email_da_empresa": i[2],
            "senha_da_empresa": i[3],
            "dominio_da_empresa": i[4],
            "senha_do_dominio_da_empresa": i[5]
        })

    users = []

    for i in resultado_users:
        users.append({
            "id_do_user": i[0],
            "nome_do_user": i[1],
            "login_do_user": i[2],
            "senha_do_user": "Precione 'Editar' para mudar",
            "hash_do_user": i[3],
            "empresas_do_user": i[4],
            "nivel_do_user": i[5]
        })

    return templates.TemplateResponse(
        "adm.html", 
        {
            "request": request, 
            "empresas": empresas, 
            "users": users, 
            "link": "arquivados", 
            "locate": "Arquivados", 
            "estado": "Arquivar"
            }
    )

class Dados(BaseModel):
    id: str
    lista: list
    tipo: str
    senha_modificada: bool

@app.get("/arquivados")

async def arquivados(request: Request):
    if not request.session.get("adm"):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    
    connector = connectar_ao_banco()

    # Pega todas as empresas cadastradas ao banco
    with connector.cursor() as cursor:
        sql = "SELECT * FROM arquivados"
        cursor.execute(sql)
        resultado_empresas = cursor.fetchall()

        sql = "SELECT * FROM users"
        cursor.execute(sql)
        resultado_users = cursor.fetchall()
    connector.close()

    empresas = []

    for i in resultado_empresas:
        empresas.append({
            "id_da_empresa": i[0],
            "nome_da_empresa": i[1],
            "email_da_empresa": i[2],
            "senha_da_empresa": i[3],
            "dominio_da_empresa": i[4],
            "senha_do_dominio_da_empresa": i[5]
        })

    users = []

    for i in resultado_users:
        users.append({
            "id_do_user": i[0],
            "nome_do_user": i[1],
            "login_do_user": i[2],
            "senha_do_user": "Precione 'Editar' para mudar",
            "hash_do_user": i[3],
            "empresas_do_user": i[4],
            "nivel_do_user": i[5]
        })

    return templates.TemplateResponse(
        "adm.html", 
        {
            "request": request,
            "empresas": empresas, 
            "users": users, 
            "link": "administracao",
            "locate": "Ativos", 
            "estado": "Ativar"
            }
    )




class Dados(BaseModel):
    id: str
    estado: str

@app.post("/arquivar")

async def arquivar(dados: Dados):
    id = dados.id
    tabela = dados.estado
    if tabela == "Arquivar":
        table_doadora = "empresas"
        table_receptora = "arquivados"
    else:
        table_doadora = "arquivados"
        table_receptora = "empresas"

    connector = connectar_ao_banco()
    with connector.cursor() as cursor:
        sql = f"SELECT * FROM {table_doadora} WHERE id = %s"
        cursor.execute(sql, id)
        empresa = cursor.fetchall()[0]

        sql = f"INSERT INTO {table_receptora} (id, nome, email, senha, dominio, senha_dominio) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, [empresa[0], empresa[1], empresa[2], empresa[3], empresa[4], empresa[5]])
        
        sql = f"DELETE FROM {table_doadora} WHERE id = %s"
        cursor.execute(sql, id)
    connector.close()


class Dados(BaseModel):
    id: str
    lista: list
    tipo: str
    senha_modificada: bool

@app.post("/salvar")

async def salvar(request: Request, dados: Dados):
    lista = dados.lista
    id = dados.id
    tipo = dados.tipo
    senha_modificada = dados.senha_modificada

    connector = connectar_ao_banco()

    if tipo == "empresa":   
        with connector.cursor() as cursor:
            sql = "UPDATE empresas SET nome = %s, email = %s, senha = %s, dominio = %s, senha_dominio = %s WHERE id = %s"
            cursor.execute(sql, (lista[1], lista[2], lista[3], lista[4], lista[5], id))
    
    if tipo == "user":
        if  senha_modificada:
            lista[2] = criptografar(lista[2])

        with connector.cursor() as cursor:
            sql = "UPDATE users SET nome = %s, login = %s, senha = %s, empresas = %s, nivel = %s WHERE id = %s"
            cursor.execute(sql, (lista[0], lista[1], lista[2], lista[3], lista[4], id))

    connector.close()

@app.get("/cria_usuario")

async def cria_usuario(request: Request):
    if not request.session.get("adm"):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "cria_user.html", {"request": request}
    )

@app.post("/criar_empresa")

async def criar_empresa(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    dominio: str = Form(...),
    senha_dominio: str = Form(...)
    ):

    connector = connectar_ao_banco()

    with connector.cursor() as cursor:
        sql = "INSERT INTO empresas (nome, email, senha, dominio, senha_dominio) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (nome, email, senha, dominio, senha_dominio))
    connector.close()

    return RedirectResponse(
        url='/administracao', 
        status_code=status.HTTP_303_SEE_OTHER
        )


@app.post("/criar_user")

async def criar_user(
    request: Request,
    nome: str = Form(...),
    login: str = Form(...),
    senha: str = Form(...),
    empresas: str = Form(...),
    nivel: str = Form(...)
    ):

    senha_hash = criptografar(senha)

    connector = connectar_ao_banco()

    with connector.cursor() as cursor:
        sql = "INSERT INTO users (nome, login, senha, empresas, nivel) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (nome, login, senha_hash, empresas, nivel))
    connector.close()

    return RedirectResponse(
        url='/administracao',
        status_code=status.HTTP_303_SEE_OTHER
        )