# Langara Timetable Scraper

This software scrapes the current and next semester of the Langara timetable
and makes it available as a JSON document.

It is implemented for [Google Cloud](https://cloud.google.com/) and uses
the following products.

* [Firestore](https://cloud.google.com/firestore)
* [Cloud Functions](https://cloud.google.com/functions)
* [Cloud Scheduler](https://cloud.google.com/scheduler)
* [Pub/Sub](https://cloud.google.com/pubsub)

## Installation

Create a new Google Cloud project or use an existing one.

Create a native Firstore database in the project. Create the
`sections` collection which will be used store the information
about each section in the timetable.

Use the Google Cloud Shell to deploy the `updateSections` Cloud Function as follows:

```shell
git clone https://github.com/koehlerb/langara-timetable-scraper.git
cd langara-timetable-scraper
gcloud functions deploy updateSections --timeout 540s --runtime python39 --trigger-topic langara_schedule_cron
```

This command also creates the "Pub/Sub" topic `langara_schedule_cron` if it
does not already exist. The `updateSections` Cloud Function
empties the `sections` collection in the Firestore database; scrapes
the timetable for the current and next semester from the Langara
website and fills the `sections` collection with the new data.

Deploy the `sections` Cloud Function as follows:

```shell
gcloud functions deploy sections --runtime python39 --trigger-http --allow-unauthenticated
```

The `sections` function retrieves timetable information from
the `sections` collection and presents it a as JSON document like:

```json
{
    "Items":
        [
            {
                "crn":"30530",
                "crse":"1154",
                "instructor":"J. Todd Stuckless",
                "sec":"001",
                "sectionId":"20213030530",
                "semester":"202130",
                "subj":"CHEM",
                "title":"Engineering Chemistry"
            },
            {
                "crn":"30521",
                "crse":"1118",
                "instructor":"James Rolke",
                "sec":"M01",
                "sectionId":"20213030521",
                "semester":"202130",
                "subj":"CHEM",
                "title":"Intermediate Chemistry"
            }
        ]
}
```

The `sections` function takes two parameters to identify the regular
studies semester and continuing studies semester. For example, the
function is invoked using a HTTP trigger like:

```shell
https://northamerica-northeast1-edtech-321122.cloudfunctions.net/sections?rssemester=202130&cssemester=020213
```

Use Cloud Scheduler to schedule a message to the `langara_schedule_cron`
Pub/Sub topic which will trigger the `updateSections` Cloud Function.
