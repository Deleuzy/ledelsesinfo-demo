// Power Query (M): hent STRAF11 direkte fra Statistikbankens åbne API, uden Python.
// Kommunerne i Nordjyllands Politikreds, hovedtyper, alle kvartaler. Kræver Web-forbindelse i Excel.
// Skrevet i hånden; endnu IKKE kørt i Excel.
let
    Kommuner = {"851","810","813","860","849","825","846","840","820"},
    Typer = {"TOT","1","11","12","13","14","3"},
    Url = "https://api.statbank.dk/v1/data/STRAF11/CSV",
    Svar = Web.Contents(Url, [Query = [
        #"OMRÅDE" = Text.Combine(Kommuner, ","),
        #"OVERTRÆD" = Text.Combine(Typer, ","),
        Tid = "*",
        valuePresentation = "Code",
        delimiter = "Semicolon"
    ]]),
    Csv = Csv.Document(Svar, [Delimiter = ";", Encoding = 65001]),
    // Svaret er langt format: OMRÅDE;OVERTRÆD;TID;INDHOLD (med BOM i starten).
    Overskrifter = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
    Omdoebt = Table.RenameColumns(Overskrifter, {{"OMRÅDE", "omraade"}, {"OVERTRÆD", "overtraed"}, {"TID", "tid"}, {"INDHOLD", "indhold"}}),
    // Statistikbanken kan skrive ".." for manglende tal; de bliver til null og skal tælles som datakvalitetsfund.
    Tal = Table.TransformColumns(Omdoebt, {{"indhold", each try Int64.From(_) otherwise null, Int64.Type}})
in
    Tal
