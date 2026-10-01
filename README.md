# 🔥 Fire Detection System on Raspberry Pi

Sistema de detecção de incêndios desenvolvido para execução em **Raspberry Pi**, utilizando uma câmera para aquisição de imagens e processamento em tempo real.

O sistema realiza a detecção de **fogo e fumaça** e disponibiliza os dados de monitoramento por meio de uma interface de visualização no **Grafana**.

---

## 📋 Requisitos

Antes de iniciar o sistema, certifique-se de que os seguintes componentes estejam disponíveis:

- Raspberry Pi;
- Fonte de alimentação compatível;
- Câmera USB;
- Monitor com conexão compatível com a saída Mini-HDMI da Raspberry Pi;
- Teclado USB;
- Mouse USB;
- Conexão Wi-Fi;
- Projeto `firedetect_project` previamente configurado na Raspberry Pi.

---

## 🚀 Passo a passo para executar o sistema

### 1. Conectar os periféricos USB

> ⚠️ **Importante:** realize as conexões com a Raspberry Pi desligada e desconectada da fonte de alimentação.

Conecte às portas USB da Raspberry Pi:

- Câmera;
- Teclado;
- Mouse.

Após realizar as conexões, verifique se os dispositivos estão corretamente conectados.

---

### 2. Conectar o monitor

Com a Raspberry Pi ainda desligada, conecte o monitor à saída **Mini-HDMI** da Raspberry Pi utilizando o cabo correspondente.

Certifique-se de que o monitor esteja ligado e configurado para a entrada de vídeo correta.

---

### 3. Ligar a Raspberry Pi

Após conectar todos os periféricos, conecte a fonte de alimentação à Raspberry Pi.

Aguarde a inicialização completa do sistema operacional.

---

### 4. Conectar a Raspberry Pi à rede Wi-Fi

No ambiente gráfico da Raspberry Pi:

1. Acesse as configurações de rede;
2. Selecione a rede Wi-Fi desejada;
3. Informe a senha;
4. Aguarde a confirmação da conexão.

A conexão de rede é necessária para os serviços de comunicação e monitoramento utilizados pelo sistema.

---

### 5. Acessar o diretório do projeto

Na Raspberry Pi, localize e abra a pasta:

```bash
firedetect_project
```

Essa pasta contém os arquivos necessários para a execução do sistema de detecção.

---

### 6. Executar o sistema

Dentro da pasta `firedetect_project`, localize o arquivo:

```bash
run.sh
```

Execute o arquivo e, quando solicitado pelo sistema operacional, selecione:

```text
Execute in Terminal
```

O script `run.sh` iniciará os componentes necessários para a execução do sistema.

---

## 📊 Acesso ao Grafana

Após a inicialização dos serviços, acesse o **Grafana**.

Na tela de autenticação, utilize:

```text
Username: admin
Password: admin
```

No primeiro acesso, o Grafana poderá solicitar a alteração da senha.

Para manter a configuração atual durante os testes, selecione:

```text
Skip
```

Após o login, acesse o dashboard configurado para acompanhar os dados provenientes do sistema de detecção.

---

## 🔥 Fluxo geral do sistema

O funcionamento geral pode ser representado da seguinte forma:

```text
Câmera
   │
   ▼
Raspberry Pi
   │
   ▼
Sistema de Detecção
   │
   ├──► Detecção de Fogo
   │
   ├──► Detecção de Fumaça
   │
   └──► Análise dos Dados
            │
            ▼
      Comunicação / Armazenamento
            │
            ▼
          Grafana
            │
            ▼
         Dashboard
```

---

## ⚠️ Observações

- Não conecte ou desconecte os principais periféricos durante a inicialização do sistema.
- Certifique-se de que a câmera foi reconhecida corretamente pela Raspberry Pi antes de executar o sistema.
- Verifique a conexão Wi-Fi antes de iniciar os serviços que dependem da rede.
- Caso a câmera não apresente imagens, verifique a conexão USB antes de reiniciar o sistema.
- Aguarde a inicialização completa dos serviços antes de acessar o dashboard.

---

## 🛠️ Troubleshooting

### Câmera não apresenta imagem

Verifique se a câmera está conectada corretamente à porta USB da Raspberry Pi.

No terminal, a disponibilidade do dispositivo de vídeo pode ser verificada com:

```bash
ls -l /dev/video*
```

### Sistema não inicia

Confirme se o arquivo `run.sh` está sendo executado dentro do diretório correto:

```bash
firedetect_project
```

Também verifique se o arquivo possui permissão de execução.

### Grafana não apresenta dados

Verifique:

- se a Raspberry Pi está conectada à rede;
- se o sistema de detecção está em execução;
- se os serviços utilizados pelo projeto foram inicializados corretamente;
- se o dashboard correto foi selecionado no Grafana.

---

## 📌 Projeto

**Fire Detection System using Raspberry Pi**

Projeto desenvolvido para detecção e monitoramento de incêndios utilizando **Visão Computacional, Deep Learning, IoT e Computação Embarcada**.
