from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS
import io
import base64
import warnings
import easyocr
from PIL import Image
from PyPDF2 import PdfReader

from src.agente import curriculo, curriculo_sumario
from src.database import log_request

# Suprimir warning do pin_memory do EasyOCR/PyTorch
warnings.filterwarnings("ignore", message=".*pin_memory.*")


# ============================================================================
# MODELOS PYDANTIC PARA RESPONSES
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Modelo de resposta para o endpoint de health check"""
    message: str = Field(
        ...,
        examples=["API de Análise de Currículos está online"],
        description="Mensagem de status da API"
    )
    status: str = Field(
        default="online",
        examples=["online"],
        description="Status da API"
    )
    version: str = Field(
        ...,
        examples=["1.0.0"],
        description="Versão da API"
    )


class FileInfo(BaseModel):
    """Informações sobre um arquivo processado"""
    filename: str = Field(
        ...,
        examples=["curriculo_joao_silva.pdf"],
        description="Nome do arquivo enviado"
    )
    content_type: str = Field(
        ...,
        examples=["application/pdf"],
        description="Tipo MIME do arquivo"
    )
    size: int = Field(
        ...,
        examples=[245678],
        description="Tamanho do arquivo em bytes",
        gt=0
    )


class CurriculoAnaliseResponse(BaseModel):
    """Modelo de resposta para análise de currículos"""
    request_id: str = Field(
        ...,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="UUID único da requisição"
    )
    user_id: str = Field(
        ...,
        examples=["user_123"],
        description="Identificador do usuário que fez a requisição"
    )
    files_processed: int = Field(
        ...,
        examples=[2],
        description="Quantidade de arquivos processados",
        ge=1
    )
    files_info: List[FileInfo] = Field(
        ...,
        description="Lista com informações dos arquivos processados"
    )
    query: str = Field(
        ...,
        examples=["Qual candidato tem mais experiência em Python?"],
        description="Pergunta realizada ou indicação de modo de sumarização"
    )
    resultado: str = Field(
        ...,
        examples=["Com base na análise dos currículos enviados..."],
        description="Resultado da análise gerada pela IA"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "user_123",
                    "files_processed": 1,
                    "files_info": [
                        {
                            "filename": "curriculo_maria_santos.pdf",
                            "content_type": "application/pdf",
                            "size": 187456
                        }
                    ],
                    "query": "[Modo: Sumarização Individual]",
                    "resultado": "============================================================\nCURRÍCULO  #1: curriculo_maria_santos.pdf - Sumário\n============================================================\n\n**Nome:** Maria Santos\n**Cargo Atual:** Desenvolvedora Full Stack Sênior\n\n**Resumo Profissional:**\nDesenvolvedora com 8 anos de experiência em desenvolvimento web, especializada em Python, JavaScript e React...\n\n**Experiência Profissional:**\n- Tech Corp (2020-2024): Full Stack Developer\n- StartupXYZ (2017-2020): Backend Developer\n\n**Formação:**\n- Bacharelado em Ciência da Computação - USP (2013-2016)"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Modelo de resposta para erros HTTP"""
    detail: str = Field(
        ...,
        examples=["Mensagem de erro detalhada"],
        description="Descrição detalhada do erro"
    )


# ============================================================================
# CONFIGURAÇÃO DA API
# ============================================================================

app = FastAPI(
    title="TechMatch - API de Análise de Currículos",
    description="""
## Teste Prático - API para Análise de Currículos com IA

**Candidato:** Sávio Afonso Rezende Guimarães
    """,
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Endpoints de verificação de status e saúde da API"
        },
        {
            "name": "Análise",
            "description": "Endpoints para processamento e análise de currículos com IA"
        }
    ],
    contact={
        "name": "Sávio Guimarães",
        "url": "https://www.linkedin.com/in/savioarguimaraes/",
    }
)

reader = easyocr.Reader(['pt', 'en'], gpu=False)


def get_file_extension(filename: str) -> str:
    return "." + filename.split(".")[-1].lower() if "." in filename else ""


def extrair_texto_imagem(conteudo_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(conteudo_bytes))

        if image.mode != 'RGB':
            image = image.convert('RGB')

        result = reader.readtext(image, detail=0)
        texto = " ".join(result)

        if not texto or texto.strip() == "":
            return ""

        return texto

    except Exception as e:
        return ""


def extrair_texto_pdf(conteudo_bytes: bytes) -> str:
    try:
        pdf_reader = PdfReader(io.BytesIO(conteudo_bytes))
        texto = ""
        for page in pdf_reader.pages:
            texto += page.extract_text() + "\n"
        return texto.strip()
    except Exception as e:
        return f"[Erro ao processar PDF: {str(e)}]"


def processar_arquivo(filename: str, conteudo: bytes) -> str:
    extensao = get_file_extension(filename)

    if extensao == ".pdf":
        return extrair_texto_pdf(conteudo)

    elif extensao in [".jpg", ".jpeg", ".png"]:
        return extrair_texto_imagem(conteudo)

    elif extensao in [".doc", ".docx"]:
        return "[Processamento de arquivos Word em desenvolvimento]"

    return "[Tipo de arquivo não suportado para extração de texto]"


@app.get(
    "/",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health Check da API",
    description="Verifica se a API está online e retorna informações de status e versão"
)
async def root():
    """
    ## Health Check

    Endpoint simples para verificar se a API está funcionando corretamente.

    **Retorna:**
    - `message`: Mensagem de status
    - `status`: Status atual da API ("online" ou "offline")
    - `version`: Versão atual da API
    """
    return {
        "message": "API de Análise de Currículos está online",
        "status": "online",
        "version": "1.0.0"
    }



@app.post(
    "/curriculo",
    response_model=CurriculoAnaliseResponse,
    tags=["Análise"],
    summary="Analisar Currículos com IA",
    description="Processa e analisa currículos usando inteligência artificial com suporte a OCR",
    responses={
        200: {
            "description": "Análise realizada com sucesso",
            "content": {
                "application/json": {
                    "examples": {
                        "sumarizacao": {
                            "summary": "Exemplo: Sumarização Individual",
                            "description": "Quando nenhuma query é fornecida, a API gera um sumário detalhado de cada currículo enviado",
                            "value": {
                                "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "user_id": "recrutador_rh_001",
                                "files_processed": 1,
                                "files_info": [
                                    {
                                        "filename": "curriculo_joao_silva.pdf",
                                        "content_type": "application/pdf",
                                        "size": 312456
                                    }
                                ],
                                "query": "[Modo: Sumarização Individual]",
                                "resultado": "============================================================\nCURRÍCULO  #1: curriculo_joao_silva.pdf - Sumário\n============================================================\n\n**Nome:** João Silva\n**Cargo Desejado:** Desenvolvedor Backend Python\n**Localização:** São Paulo, SP\n\n**Resumo Profissional:**\nDesenvolvedor Backend com 5 anos de experiência em Python, especializado em FastAPI, Django e microserviços. Experiência sólida com AWS, Docker e Kubernetes.\n\n**Experiência Profissional:**\n• **TechCorp Brasil** (2021-2024) - Senior Backend Developer\n  - Desenvolvimento de APIs REST com FastAPI\n  - Implementação de arquitetura de microserviços\n  - Redução de 40% no tempo de resposta das APIs\n\n• **StartupXYZ** (2019-2021) - Backend Developer\n  - Desenvolvimento com Django e PostgreSQL\n  - Integração com serviços AWS (S3, Lambda, RDS)\n\n**Formação Acadêmica:**\n• Bacharelado em Ciência da Computação - USP (2015-2018)\n\n**Habilidades Técnicas:**\n- Linguagens: Python, SQL, JavaScript\n- Frameworks: FastAPI, Django, Flask\n- Cloud: AWS (EC2, S3, Lambda, RDS)\n- DevOps: Docker, Kubernetes, CI/CD\n- Bancos: PostgreSQL, MongoDB, Redis\n\n**Certificações:**\n• AWS Certified Solutions Architect (2023)\n• Python Professional Certificate (2022)"
                            }
                        },
                        "comparacao": {
                            "summary": "Exemplo: Análise Comparativa",
                            "description": "Quando uma query específica é fornecida, a API compara múltiplos currículos e responde à pergunta",
                            "value": {
                                "request_id": "f7e8d9c0-b1a2-3456-789a-bcdef0123456",
                                "user_id": "gerente_ti_002",
                                "files_processed": 3,
                                "files_info": [
                                    {
                                        "filename": "curriculo_maria_santos.pdf",
                                        "content_type": "application/pdf",
                                        "size": 245890
                                    },
                                    {
                                        "filename": "curriculo_carlos_oliveira.jpg",
                                        "content_type": "image/jpeg",
                                        "size": 512340
                                    },
                                    {
                                        "filename": "curriculo_ana_costa.png",
                                        "content_type": "image/png",
                                        "size": 678123
                                    }
                                ],
                                "query": "Qual candidato tem mais experiência com FastAPI e arquitetura de microserviços?",
                                "resultado": "Com base na análise detalhada dos três currículos enviados, aqui está a comparação:\n\n**RANKING DE EXPERIÊNCIA COM FASTAPI E MICROSERVIÇOS:**\n\n🥇 **1º LUGAR: Maria Santos** (curriculo_maria_santos.pdf)\n• **Experiência com FastAPI:** 4 anos\n• **Experiência com Microserviços:** 5 anos\n• **Destaques:**\n  - Trabalhou como Tech Lead em projeto de migração de monolito para microserviços usando FastAPI\n  - Implementou 12+ microserviços em produção\n  - Mentor de time de 5 desenvolvedores em FastAPI\n  - Palestrou em conferências sobre arquitetura de microserviços\n  - Contribui para projetos open-source relacionados a FastAPI\n\n🥈 **2º LUGAR: Carlos Oliveira** (curriculo_carlos_oliveira.jpg)\n• **Experiência com FastAPI:** 2 anos\n• **Experiência com Microserviços:** 3 anos\n• **Destaques:**\n  - Desenvolveu APIs REST com FastAPI em projetos comerciais\n  - Experiência com Docker e Kubernetes para deploy de microserviços\n  - Conhecimento em patterns de comunicação entre serviços (gRPC, RabbitMQ)\n\n🥉 **3º LUGAR: Ana Costa** (curriculo_ana_costa.png)\n• **Experiência com FastAPI:** 1 ano\n• **Experiência com Microserviços:** 2 anos\n• **Destaques:**\n  - Trabalhou principalmente com Django, mas tem projetos recentes em FastAPI\n  - Conhecimento básico de arquitetura de microserviços\n  - Interesse em aprender mais sobre o ecossistema FastAPI\n\n**RECOMENDAÇÃO:**\nMaria Santos é a candidata mais qualificada para posições que exigem expertise avançada em FastAPI e microserviços. Carlos Oliveira seria uma ótima segunda opção com experiência sólida. Ana Costa seria adequada para posições júnior/pleno com mentorias."
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Formato de arquivo não suportado",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Arquivo curriculo.txt tem extensão não permitida. Permitidos: PDF, JPG, PNG, DOCX"
                    }
                }
            }
        },
        422: {
            "description": "Erro de validação dos parâmetros",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "missing",
                                "loc": ["body", "user_id"],
                                "msg": "Field required",
                                "input": None
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Erro interno no processamento",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Erro ao processar requisição: Connection timeout ao conectar com a IA"
                    }
                }
            }
        }
    }
)
async def analisar_curriculo(
    files: List[UploadFile] = File(..., description="Lista de arquivos de currículos (PDF, JPG, PNG)"),
    query: Optional[str] = Form(None, description="Pergunta específica sobre os currículos. Se vazio ou omitido, gera sumário individual de cada currículo"),
    request_id: Optional[str] = Form(None, description="ID único da requisição (UUID ou string). Se não fornecido, será gerado automaticamente"),
    user_id: str = Form(..., description="Identificador do usuário que está fazendo a requisição")
):
    """
    ## 🔍 Análise Inteligente de Currículos

    Endpoint principal para processamento e análise de currículos usando inteligência artificial.

    ### 📝 Modos de Operação

    **1. Modo Sumarização (query vazio ou None):**
    - Gera sumário estruturado individual de cada currículo
    - Extrai informações-chave: nome, cargo, experiências, formação, habilidades
    - Ideal para triagem inicial de candidatos

    **2. Modo Consulta (query com pergunta):**
    - Analisa todos os currículos em conjunto
    - Responde perguntas específicas sobre os candidatos
    - Faz comparações e rankings quando solicitado
    - Exemplos de perguntas:
      - "Qual candidato tem mais experiência em Python?"
      - "Compare as formações acadêmicas dos candidatos"
      - "Quem tem certificações relevantes para DevOps?"

    ### 📤 Upload de Arquivos

    - **Formatos aceitos:** PDF, JPG, JPEG, PNG
    - **Múltiplos arquivos:** Sim (envie vários currículos de uma vez)
    - **Processamento:** Extração de texto com OCR para imagens

    ### 🔄 Fluxo de Processamento

    1. Valida formatos dos arquivos
    2. Extrai texto (PDF direto, OCR para imagens)
    3. Processa com IA conforme o modo selecionado
    4. Registra log da requisição no MongoDB
    5. Retorna análise estruturada

    ### ✅ Response

    Retorna objeto JSON com:
    - `request_id`: UUID único da requisição
    - `user_id`: Identificador do usuário
    - `files_processed`: Quantidade de arquivos processados
    - `files_info`: Lista com detalhes de cada arquivo
    - `query`: Pergunta realizada ou indicador de modo
    - `resultado`: Análise completa gerada pela IA

    ### ⚠️ Tratamento de Erros

    - **400**: Formato de arquivo não suportado
    - **422**: Erro de validação (parâmetros obrigatórios ausentes ou inválidos)
    - **500**: Erro interno no processamento (falha de IA, MongoDB, etc.)
    """
    try:
        if request_id is None:
            request_uuid = uuid4()
        else:
            try:
                request_uuid = UUID(request_id)
            except ValueError:
                request_uuid = uuid5(NAMESPACE_DNS, request_id)

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
        arquivos_processados = []

        for file in files:
            file_extension = get_file_extension(file.filename)

            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Arquivo {file.filename} tem extensão não permitida. Permitidos: PDF, JPG, PNG, DOCX"
                )

            conteudo = await file.read()

            texto_extraido = processar_arquivo(file.filename, conteudo)

            arquivos_processados.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(conteudo),
                "texto": texto_extraido,
                "bytes_originais": conteudo,
                "extensao": file_extension
            })

        deve_sumarizar = (
            query is None or
            query.strip() == "" or
            query.strip().lower() == "string"
        )

        if deve_sumarizar:
            sumarios = []
            for i, arq in enumerate(arquivos_processados, 1):
                ocr_falhou = not arq["texto"] or arq["texto"].strip() == ""

                if ocr_falhou and arq["extensao"] in [".jpg", ".jpeg", ".png"]:
                    image_base64 = base64.b64encode(arq["bytes_originais"]).decode('utf-8')

                    mime_type = "image/jpeg" if arq["extensao"] in [".jpg", ".jpeg"] else "image/png"

                    resultado = await curriculo_sumario.ainvoke({
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Analise este currículo em formato de imagem e gere o sumário completo seguindo o formato solicitado:"},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
                            ]
                        }]
                    })
                else:
                    resultado = await curriculo_sumario.ainvoke({
                        "messages": [{"role": "user", "content": arq["texto"]}]
                    })

                if isinstance(resultado, dict) and "messages" in resultado:
                    sumario_individual = resultado["messages"][-1].content if resultado["messages"] else "Sem resposta"
                else:
                    sumario_individual = str(resultado)

                sumario_formatado = f"\n{'='*60}\n"
                sumario_formatado += f"CURRÍCULO  #{i}: {arq['filename']} - Sumário\n"
                sumario_formatado += f"{'='*60}\n"
                sumario_formatado += f"{sumario_individual}\n"
                sumarios.append(sumario_formatado)

            resposta_agente = "\n".join(sumarios)

        else:
            content_parts = [{"type": "text", "text": f"PERGUNTA/CONSULTA: {query}\n"}]

            for i, f in enumerate(arquivos_processados, 1):
                ocr_falhou = not f["texto"] or f["texto"].strip() == ""

                header = f"\n{'='*60}\n"
                header += f"CURRÍCULO #{i}: {f['filename']}\n"
                header += f"{'='*60}\n"
                content_parts.append({"type": "text", "text": header})

                if ocr_falhou and f["extensao"] in [".jpg", ".jpeg", ".png"]:
                    image_base64 = base64.b64encode(f["bytes_originais"]).decode('utf-8')
                    mime_type = "image/jpeg" if f["extensao"] in [".jpg", ".jpeg"] else "image/png"

                    content_parts.append({
                        "type": "text",
                        "text": "[Imagem do currículo - OCR não disponível, analisando visualmente]"
                    })
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}
                    })
                else:
                    content_parts.append({"type": "text", "text": f"{f['texto']}\n"})

            resultado = await curriculo.ainvoke({
                "messages": [{"role": "user", "content": content_parts}]
            })

            if isinstance(resultado, dict) and "messages" in resultado:
                resposta_agente = resultado["messages"][-1].content if resultado["messages"] else "Sem resposta"
            else:
                resposta_agente = str(resultado)

        query_para_log = query if query and query.strip() and query.strip().lower() != "string" else "[Modo: Sumarização Individual]"

        try:
            await log_request(
                request_id=str(request_uuid),
                user_id=user_id,
                query=query_para_log,
                resultado=resposta_agente,
                files_count=len(arquivos_processados),
                status="success"
            )
        except Exception as log_error:
            print(f"Erro ao salvar log no MongoDB: {log_error}")

        return {
            "request_id": str(request_uuid),
            "user_id": user_id,
            "files_processed": len(arquivos_processados),
            "files_info": [
                {
                    "filename": f["filename"],
                    "content_type": f["content_type"],
                    "size": f["size"]
                }
                for f in arquivos_processados
            ],
            "query": query_para_log,
            "resultado": resposta_agente
        }

    except HTTPException:
        raise
    except Exception as e:
        try:
            query_erro = query if 'query' in locals() and query and query.strip() and query.strip().lower() != "string" else "[Modo: Sumarização Individual]"

            await log_request(
                request_id=str(request_uuid) if 'request_uuid' in locals() else "unknown",
                user_id=user_id if 'user_id' in locals() else "unknown",
                query=query_erro,
                resultado=f"Erro: {str(e)}",
                files_count=len(arquivos_processados) if 'arquivos_processados' in locals() else 0,
                status="error"
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
