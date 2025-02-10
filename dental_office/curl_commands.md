# cURL Commands for the Appointments API

Assuming your server is running at `http://10.10.2.194:5000` and the API token is `mysecrettoken`, use the following commands:

---

## Get All Appointments

**Using the Authorization header:**

~~~cmd
curl -X GET -H "Authorization: Bearer mysecrettoken" "http://10.10.2.194:5000/api/appointments"
~~~

**Using a query parameter:**

~~~cmd
curl -X GET "http://10.10.2.194:5000/api/appointments?token=mysecrettoken"
~~~

---

## Add a New Appointment

~~~cmd
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer mysecrettoken" -d "{\"title\": \"Dental Cleaning\", \"start_time\": \"2025-03-10T09:00\", \"end_time\": \"2025-03-10T10:00\", \"customer_name\": \"John Doe\", \"customer_phone\": \"123-456-7890\", \"customer_email\": \"john@example.com\"}" "http://10.10.2.194:5000/api/appointments"
~~~

---

## Update (Edit) an Appointment

_For example, updating the appointment with ID 1:_

~~~cmd
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer mysecrettoken" -d "{\"title\": \"Rescheduled Cleaning\", \"start_time\": \"2025-03-10T10:00\", \"end_time\": \"2025-03-10T11:00\"}" "http://10.10.2.194:5000/api/appointments/1"
~~~

---

## Delete an Appointment

_For example, deleting the appointment with ID 1:_

~~~cmd
curl -X DELETE -H "Authorization: Bearer mysecrettoken" "http://10.10.2.194:5000/api/appointments/1"
~~~
