# Getting Started

### Reference Documentation
For further reference, please consider the following sections:

* [Official Apache Maven documentation](https://maven.apache.org/guides/index.html)
* [Spring Boot Maven Plugin Reference Guide](https://docs.spring.io/spring-boot/4.0.4/maven-plugin)
* [Create an OCI image](https://docs.spring.io/spring-boot/4.0.4/maven-plugin/build-image.html)
* [Spring Web](https://docs.spring.io/spring-boot/4.0.4/reference/web/servlet.html)
* [Spring Data JPA](https://docs.spring.io/spring-boot/4.0.4/reference/data/sql.html#data.sql.jpa-and-spring-data)

### Guides
The following guides illustrate how to use some features concretely:

* [Building a RESTful Web Service](https://spring.io/guides/gs/rest-service/)
* [Serving Web Content with Spring MVC](https://spring.io/guides/gs/serving-web-content/)
* [Building REST services with Spring](https://spring.io/guides/tutorials/rest/)
* [Accessing Data with JPA](https://spring.io/guides/gs/accessing-data-jpa/)
* [Accessing data with MySQL](https://spring.io/guides/gs/accessing-data-mysql/)

## Run the attendance project on Windows

1. Make sure MySQL is running and the `attendance_system` database exists. Copy `src/main/resources/application.properties.example` to `src/main/resources/application.properties` and set your local `DB_PASSWORD` environment variable before starting the API.
2. In `Backend_api`, run `.\mvnw.cmd test`, then start the API with `.\mvnw.cmd spring-boot:run`. Keep this terminal open.
3. In the project root, install Python packages with `python -m pip install -r requirements.txt`.
4. Run `python main.py` from the project root so it can find `Students.csv`, `images`, and `attendance.db`.

The face-recognition app saves attendance to SQLite/`Attendance.csv` and sends new marks to `http://localhost:8080/api/mark-attendance` for MySQL storage. If the API is unavailable, the attendance is still saved locally and the app prints a backend-sync warning. Set `ATTENDANCE_API_URL` in the Python process environment to use a different API address.

`Students.csv` must contain `ROLL`, `NAME`, `PHONE`, and `PARENT_PHONE` columns. Keep this file and face images private; add your own `images` folder locally with one face image per student. The percentage is based on the distinct dates currently recorded in SQLite; for a calendar-accurate percentage, class days and holidays must also be tracked.

The root `.gitignore` excludes local database credentials, student/contact CSVs, attendance records, face images, and generated build output. Do not remove these exclusions when publishing the source.

### Maven Parent overrides

Due to Maven's design, elements are inherited from the parent POM to the project POM.
While most of the inheritance is fine, it also inherits unwanted elements like `<license>` and `<developers>` from the parent.
To prevent this, the project POM contains empty overrides for these elements.
If you manually switch to a different parent and actually want the inheritance, you need to remove those overrides.
