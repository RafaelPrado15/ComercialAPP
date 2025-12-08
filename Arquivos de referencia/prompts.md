Gostaria de que você criasse um app web, como portal de uma empresa, ele deve ter a tela de login abaixo:
@login.html

também deve ter uma identidade visual parecida com o ar que adicionei.

Ele deve ser construido com um backend em flask e um frontend em html, css, js e bootstrap.
Após o login ele deve ser redirecionado para uma tela de menu, que deve ter as opções abaixo:
- Rastreio
- Pedidos
- Notas
(Obs.: os buttons acima só devem ser visiveis caso o usuario esteja vinculado a uma empresa, caso contrario deve avisar que ele não esta vinculado a nenhuma empresa.)
- Sair

A tela de rastreio deve funcionar da seguinte forma:
Ela deve funcionar como um quadro kanban, com as seguintes colunas:
- Pendentes
- Em Fábrica
- Faturado
E deve executar a seguinte query:
SELECT NumeroPedido, Vendedor,StatusPedido, Emissao, PrevisaoFaturamento, Cliente FROM N8N_InformacoesPedidos ()


A tela de pedidos deve funcionar da seguinte forma:
Ela deve ter uma listagem dos pedidos em ordem decrescente e ao clicar em um pedido deve abrir uma tela de detalhes.
Credenciais DB SQL Server:
user: basico
password: uSxT@JWG@VMn
Observação: o campo @codCliente deve ser o codigo da empresa em nosso banco de dados.
query:
    DECLARE @notaFiscal VARCHAR(15) = ''
    DECLARE @codCliente VARCHAR(6) = '000189' 
    DECLARE @codRepres VARCHAR(6) = '' 
    DECLARE @pedido VARCHAR(10) = ''
    DECLARE @dataMinima VARCHAR(8) = '20250101';

    SELECT
        F2_DOC AS NUM_NOTA,
        F2_VEND1,
        A3_NOME,
        F2_EMISSAO,
        F2_CLIENTE,
        A1_NOME,
        F2_VALBRUT,
        SD2APP.D2_PEDIDO,
        INFO_PED.StatusPedido,
        F2_CHVNFE
    FROM SF2010 AS SF2 WITH(NOLOCK)
    INNER JOIN SA3010 AS SA3 WITH(NOLOCK)
        ON SA3.A3_COD = SF2.F2_VEND1
        AND SA3.D_E_L_E_T_ = ''
        AND SA3.A3_MSBLQL <> '1'
    INNER JOIN SA1010 AS SA1 WITH(NOLOCK)
        ON SA1.A1_COD = SF2.F2_CLIENTE
        AND SA1.D_E_L_E_T_ = ''
        AND SA1.A1_MSBLQL <> '1'
    INNER JOIN (
        SELECT
        DISTINCT(D2_PEDIDO) AS D2_PEDIDO,
        D2_DOC,
        D2_LOJA,
        D2_SERIE,
        D2_CLIENTE
        FROM SD2010 AS SD2 WITH(NOLOCK)
        WHERE SD2.D_E_L_E_T_ = ''
        AND SD2.D2_PEDIDO <> ''
        ) AS SD2APP
        ON SD2APP.D2_DOC =  SF2.F2_DOC
        AND SD2APP.D2_SERIE = SF2.F2_SERIE
        AND SD2APP.D2_LOJA = SF2.F2_LOJA
        AND SD2APP.D2_CLIENTE = SF2.F2_CLIENTE
    LEFT JOIN N8N_InformacoesPedidos() AS INFO_PED
        ON INFO_PED.NumeroPedido = SD2APP.D2_PEDIDO
        AND INFO_PED.Vendedor = SF2.F2_VEND1
    WHERE SF2.D_E_L_E_T_ = ''
        AND (@codRepres = '' OR SF2.F2_VEND1 = @codRepres)
        AND (@pedido = '' OR SD2APP.D2_PEDIDO = @pedido)
        AND (@notaFiscal ='' OR SF2.F2_DOC = @notaFiscal)
        AND (@codCliente ='' OR SF2.F2_CLIENTE = @codCliente)
        AND SF2.F2_EMISSAO >= @dataMinima
        --AND INFO_PED.StatusPedido IS NOT NULL
    ORDER BY SF2.F2_EMISSAO DESC


A tela de notas deve funcionar da seguinte forma:
Ela deve ter uma listagem das notas em ordem decrescente e ao clicar em uma nota deve abrir uma tela de detalhes.
Credenciais DB:
user: basico
password: uSxT@JWG@VMn
query: 
    SELECT
        F2_DOC AS NUM_NOTA,
        F2_VEND1,
        A3_NOME,
        F2_EMISSAO,
        F2_CLIENTE,
        A1_NOME,
        F2_VALBRUT,
        SD2APP.D2_PEDIDO,
        INFO_PED.StatusPedido,
        F2_CHVNFE
    FROM SF2010 AS SF2 WITH(NOLOCK)
    INNER JOIN SA3010 AS SA3 WITH(NOLOCK)
        ON SA3.A3_COD = SF2.F2_VEND1
        AND SA3.D_E_L_E_T_ = ''
        AND SA3.A3_MSBLQL <> '1'
    INNER JOIN SA1010 AS SA1 WITH(NOLOCK)
        ON SA1.A1_COD = SF2.F2_CLIENTE
        AND SA1.D_E_L_E_T_ = ''
        AND SA1.A1_MSBLQL <> '1'
    INNER JOIN (
        SELECT
        DISTINCT(D2_PEDIDO) AS D2_PEDIDO,
        D2_DOC,
        D2_LOJA,
        D2_SERIE,
        D2_CLIENTE
        FROM SD2010 AS SD2 WITH(NOLOCK)
        WHERE SD2.D_E_L_E_T_ = ''
        AND SD2.D2_PEDIDO <> ''
        ) AS SD2APP
        ON SD2APP.D2_DOC =  SF2.F2_DOC
        AND SD2APP.D2_SERIE = SF2.F2_SERIE
        AND SD2APP.D2_LOJA = SF2.F2_LOJA
        AND SD2APP.D2_CLIENTE = SF2.F2_CLIENTE
    LEFT JOIN N8N_InformacoesPedidos() AS INFO_PED
        ON INFO_PED.NumeroPedido = SD2APP.D2_PEDIDO
        AND INFO_PED.Vendedor = SF2.F2_VEND1
    WHERE SF2.D_E_L_E_T_ = ''
        AND (@codRepres = '' OR SF2.F2_VEND1 = @codRepres)
        AND (@pedido = '' OR SD2APP.D2_PEDIDO = @pedido)
        AND (@notaFiscal ='' OR SF2.F2_DOC = @notaFiscal)
        AND (@codCliente ='' OR SF2.F2_CLIENTE = @codCliente)
        AND SF2.F2_EMISSAO >= @dataMinima
        --AND INFO_PED.StatusPedido IS NOT NULL
    ORDER BY SF2.F2_EMISSAO DESC



Deve ser feito um banco de dados em sql lite. O banco de dados deve ter as seguintes tabelas:
- Usuarios
- UsuariosEmpresas
- Empresas

Gostaria de vincular o usuario a empresa.