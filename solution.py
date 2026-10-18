import os
import requests
import folium

BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"


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
        timeout=30
    )
    resposta.raise_for_status()

    if resposta.text.strip().lower() != "true":
        raise ValueError(
            "Falha na autenticação. Confira se o token é válido."
        )

    print("Autenticação realizada!")


    resposta = sessao.get(
        f"{BASE_URL}/Linha/Buscar",
        params={"termosBusca": "8000"},
        timeout=30
    )
    resposta.raise_for_status()
    linhas = resposta.json()

    if not linhas:
        raise ValueError("A API não retornou linhas para a busca 8000.")


    linha_escolhida = None
    paradas = []

    for linha in linhas:
        codigo = linha["cl"]

        resposta = sessao.get(
            f"{BASE_URL}/Parada/BuscarParadasPorLinha",
            params={"codigoLinha": codigo},
            timeout=30
        )
        resposta.raise_for_status()
        paradas_teste = resposta.json()

        if paradas_teste:
            linha_escolhida = linha
            paradas = paradas_teste
            break

    if linha_escolhida is None:
        raise ValueError(
            "Nenhuma das linhas encontradas retornou paradas."
        )

    codigo_linha = linha_escolhida["cl"]
    print("Linha selecionada:", linha_escolhida["lt"])
    print("Origem:", linha_escolhida["tp"])
    print("Destino:", linha_escolhida["ts"])
    print("Quantidade de paradas:", len(paradas))


    resposta = sessao.get(
        f"{BASE_URL}/Posicao/Linha",
        params={"codigoLinha": codigo_linha},
        timeout=30
    )
    resposta.raise_for_status()
    dados = resposta.json()
    onibus = dados.get("vs", [])

    print("Ônibus encontrados:", len(onibus))


    latitude = sum(p["py"] for p in paradas) / len(paradas)
    longitude = sum(p["px"] for p in paradas) / len(paradas)

    mapa = folium.Map(
    location=[latitude, longitude],
    zoom_start=13,
    tiles="CartoDB positron"

    )

    grupo_paradas = folium.FeatureGroup(name="Paradas")

    for parada in paradas:
        folium.Marker(
            location=[parada["py"], parada["px"]],
            popup=(
                f"<b>Parada:</b> {parada.get('np', 'Sem nome')}<br>"
                f"<b>Endereço:</b> {parada.get('ed', 'Não informado')}"
            ),
            tooltip=parada.get("np", "Parada"),
            icon=folium.Icon(
                color="blue",
                icon="info-sign"
            )
        ).add_to(grupo_paradas)

    grupo_paradas.add_to(mapa)


    grupo_onibus = folium.FeatureGroup(name="Ônibus em circulação")

    for veiculo in onibus:
        folium.Marker(
            location=[veiculo["py"], veiculo["px"]],
            popup=(
                f"<b>Prefixo:</b> {veiculo.get('p', 'Não informado')}<br>"
                f"<b>Acessível:</b> "
                f"{'Sim' if veiculo.get('a') else 'Não'}<br>"
                f"<b>Última atualização:</b> "
                f"{veiculo.get('ta', 'Não informada')}"
            ),
            tooltip=f"Ônibus {veiculo.get('p', '')}",
            icon=folium.Icon(
                color="red",
                icon="bus",
                prefix="fa"
            )
        ).add_to(grupo_onibus)

    grupo_onibus.add_to(mapa)

    folium.LayerControl().add_to(mapa)


    mapa.save("mapa_frota.html")

    print("Mapa salvo em mapa_frota.html")
    print("Abra esse arquivo no navegador para visualizar.")


if __name__ == "__main__":
    criar_mapa()
