# Teste Prático - API de Análise de Currículos com IA
## Candidato: Sávio Afonso Rezende Guimarães

## Descrição:
- API REST para análise de currículos usando inteligência artificial com OCR. Suporta PDF, JPG, PNG e DOCX. O currículo é enviado para a API, que extrai o texto usando OCR e envia para um agente construído em Langchain, que analisa e compara os currículos. Caso o OCR falhe por algum motivo, o arquivo binário é passado diratamente para o agente (multimodal).

## Stack

- API: FastAPI
- OCR: EasyOCR
- LLM: gpt-4.1
- Framework: Langchain
- Banco de dados: MongoDB

## Justificativa

- LLM: Foi escolhido chamar LLM via API da OpenAI em detrimento do deploy de modelos locais devido a possíveis limitações de hardware do ambiente.
- OCR: EasyOCR foi escolhido devido à sua facilidade de implementação, não sendo necessário instalar aplicativos externos ou configurar microsserviços adicionais.
- Framework: Langchain: Optei pelo uso do Framework Langchain devido à sua flexibilidade, possibilitando escalar em complexidade futuramente se necessário.
- MongoDB: Escolhido devido à facilidade de implementação local, consumindo poucos recursos e permitindo escalabilidade horizontal se necessário.

## Como baixar e utilizar

### Pré Requisitos

Certifique-se de ter instalado:

- [Git](https://git-scm.com/downloads)
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Chave da OpenAI API ([obter aqui](https://platform.openai.com/api-keys))

### Passo-a-passo

#### 1. Clonar o repositório

```bash
# Clone o projeto
git clone https://github.com/savioarguimaraes/api-analise-curriculo.git

```
#### 2. Entre na pasta 'api-analise-curriculo' e renomeie o arquivo .env.example para .env

#### 3. Abra o arquivo .env e insira uma chave de API da OpenAI

#### 4. No terminal, entre na pasta 'api-analise-curriculo' e execute o comando:

```bash
# Subir os containers
docker-compose up --build
```
#### 5. Aguarde até que o deploy esteja completo.

#### 6. Teste a API

- Para verificar se está funcionando, acesse http://localhost:8000
- Para acessar a documentação Swagger e testar, acesse http://localhost:8000/docs
- Para acessar a documentação Redoc, acesse http://localhost:8000/redoc

#### 7. Confira os logs no MongoDB

### Teste Rápido via Swagger

1. Acesse: http://localhost:8000/docs
2. Clique em **POST /curriculo**
3. Clique em **"Try it out"**
4. Faça upload de um ou mais arquivos de currículos
5. Preencha o `user_id` (ex: "teste_user")
6. Clique em **"Execute"**
