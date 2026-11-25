const source = "https://open.canada.ca/data/en/dataset/0032ce54-c5dd-4b66-99a0-320a7b5e99f2";
export const config = {
  source,
  apiGateway: "https://coolcode-visitor-api.jeffdyer.workers.dev",
  maxSavedCaptures: 30,
  map: false,
  introTitle: "Look up a corporation",
  idLabel: "Corporation number",
  dateLabel: "Anniversary",
  fields: ["Second legal-name form", "Governing legislation", "Status detail", "Last annual filing year", "Last annual meeting"],
  officialLabel: "Open Corporations Canada search ↗",
  officialLink: () => "https://ised-isde.canada.ca/cc/lgcy/fdrlCrpSrch.html?locale=en_CA",
  examples: [
    ["Early internet", "internet", "inactive-or-dissolved-cbca"],
    ["Telegraph", "telegraph", ""],
    ["Multimedia", "multimedia", "inactive-or-dissolved-cbca"],
    ["Amalgamated", "amalgamated", "inactive-or-dissolved-cbca"],
    ["Old chambers of commerce", "chamber of commerce", "inactive-or-dissolved-non-cbca"],
  ],
};
