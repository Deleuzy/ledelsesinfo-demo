// Power Query (M): indlæs anmeldelser pr. kvartal fra pipeline-outputtet.
// Brug: Excel > Data > Hent data > Tom forespørgsel > Avanceret editor, indsæt, og ret FilSti.
// Skrevet i hånden; endnu IKKE kørt i Excel. Kør den og ret fejl, før den bruges.
let
    FilSti = "C:\\data\\ledelsesinfo-demo\\output\\anmeldelser_kvartal.csv",
    Kilde = Csv.Document(File.Contents(FilSti), [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.None]),
    Overskrifter = Table.PromoteHeaders(Kilde, [PromoteAllScalars = true]),
    Typer = Table.TransformColumnTypes(
        Overskrifter,
        {{"omraade", type text}, {"omraade_navn", type text}, {"overtraed", type text},
         {"type_navn", type text}, {"tid", type text}, {"indhold", Int64.Type}}
    ),
    Dato = Table.TransformColumns(Typer, {{"kvartal_start", each Date.FromText(_, [Format = "yyyy-MM-dd"]), type date}}),
    // Kun kredsens 9 kommuner og kredsen selv (regionstallet indeholder også Thisted og Morsø).
    Kreds = Table.SelectRows(Dato, each List.Contains({"851","810","813","860","849","825","846","840","820","KREDS"}, [omraade])),
    Aar = Table.AddColumn(Kreds, "aar", each Date.Year([kvartal_start]), Int64.Type),
    Kvartal = Table.AddColumn(Aar, "kvartal", each Date.QuarterOfYear([kvartal_start]), Int64.Type)
in
    Kvartal
