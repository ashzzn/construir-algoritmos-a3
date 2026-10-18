import os
import requests
import folium

BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"

LINHAS_DOS_SLIDES = {2506, 841, 33609, 2273}


def criar_mapa():
    token = os.getenv("SPTRANS_TOKEN")

    if not token:
        raise ValueError(
            "Configure a variável de ambiente SPTRANS_TOKEN."
        )

    sessao = requests.Session()

    resposta = sessao.post(
        f"{BASE_URL}/Login/Autenticar",
        params={"token": token},
        timeout=20
    )
    resposta.raise_for_status()

    if resposta.text.strip().lower() != "true":
        raise ValueError(
            "Falha na autenticação. Confira seu token da SPTrans."
        )

    print("Autenticação realizada com sucesso!")

    resposta = sessao.get(
        f"{BASE_URL}/Linha/Buscar",
        params={"termosBusca": "8000"},
        timeout=20
    )
    resposta.raise_for_status()

    linhas = resposta.json()

    if not linhas:
        raise ValueError(
            "Nenhuma linha encontrada para o termo 8000. "
            "Tente outro termo de busca."
        )

    linha_escolhida = None
    paradas = []

    for linha in linhas:
        codigo = linha.get("cl")

        if codigo is None or codigo in LINHAS_DOS_SLIDES:
            continue

        resposta_paradas = sessao.get(
            f"{BASE_URL}/Parada/BuscarParadasPorLinha",
            params={"codigoLinha": codigo},
            timeout=20
        )
        resposta_paradas.raise_for_status()

        paradas_candidatas = resposta_paradas.json()

        if paradas_candidatas:
            linha_escolhida = linha
            paradas = paradas_candidatas
            break

    if linha_escolhida is None:
        raise ValueError(
            "Não foi encontrada uma linha diferente das usadas nos "
            "slides com paradas cadastradas. Tente alterar o termo "
            "de busca ou conferir os códigos das linhas disponíveis."
        )

    codigo_linha = linha_escolhida["cl"]

    print(
        f"Linha selecionada: {linha_escolhida.get('lt', 'Sem letreiro')}"
    )
    print(f"Código da linha: {codigo_linha}")
    print(f"Paradas encontradas: {len(paradas)}")

    coordenadas = []

    for parada in paradas:
        try:
            latitude = float(parada.get("py", 0))
            longitude = float(parada.get("px", 0))

            if latitude != 0 and longitude != 0:
                coordenadas.append((latitude, longitude))
        except (TypeError, ValueError):
            continue

    if not coordenadas:
        raise ValueError(
            "A linha selecionada não possui coordenadas válidas."
        )

    centro_lat = sum(lat for lat, lon in coordenadas) / len(coordenadas)
    centro_lon = sum(lon for lat, lon in coordenadas) / len(coordenadas)

    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=13
    )

    grupo_paradas = folium.FeatureGroup(name="Paradas de ônibus")

    for parada in paradas:
        try:
            latitude = float(parada.get("py", 0))
            longitude = float(parada.get("px", 0))

            if latitude == 0 or longitude == 0:
                continue

            nome = parada.get("np", "Parada sem nome")
            codigo_parada = parada.get("cp", "Não informado")

            folium.Marker(
                location=[latitude, longitude],
                popup=(
                    f"<b>{nome}</b><br>"
                    f"Código da parada: {codigo_parada}"
                ),
                tooltip=nome,
                icon=folium.Icon(
                    color="blue",
                    icon="info-sign"
                )
            ).add_to(grupo_paradas)

        except (TypeError, ValueError):
            continue

    grupo_paradas.add_to(mapa)

    resposta_posicoes = sessao.get(
        f"{BASE_URL}/Posicao/Linha",
        params={"codigoLinha": codigo_linha},
        timeout=20
    )
    resposta_posicoes.raise_for_status()

    dados = resposta_posicoes.json()
    veiculos = dados.get("vs", [])

    print(f"Ônibus encontrados em tempo real: {len(veiculos)}")

    grupo_onibus = folium.FeatureGroup(name="Ônibus em tempo real")

    for veiculo in veiculos:
        try:
            latitude = float(veiculo.get("py", 0))
            longitude = float(veiculo.get("px", 0))

            if latitude == 0 or longitude == 0:
                continue

            prefixo = veiculo.get("p", "Não informado")

            folium.Marker(
                location=[latitude, longitude],
                popup=(
                    f"<b>Ônibus</b><br>"
                    f"Prefixo: {prefixo}<br>"
                    f"Linha: {linha_escolhida.get('lt', 'Não informado')}"
                ),
                tooltip=f"Ônibus {prefixo}",
                icon=folium.Icon(
                    color="red",
                    icon="bus",
                    prefix="fa"
                )
            ).add_to(grupo_onibus)

        except (TypeError, ValueError):
            continue

    grupo_onibus.add_to(mapa)

    folium.LayerControl().add_to(mapa)

    arquivo = "mapa_frota.html"
    mapa.save(arquivo)

    print(f"Mapa salvo em: {os.path.abspath(arquivo)}")
    print("Abra o arquivo mapa_frota.html no navegador.")

    return mapa


if __name__ == "__main__":
    criar_mapa()

#estou executando em ambiente virtual
