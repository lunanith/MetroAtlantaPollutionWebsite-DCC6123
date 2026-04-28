# Metro Atlanta Pollution Website
**AI-Driven / GIS-Based Research & Educational Support Tool**
**Team DCC-6123 | Client: Center for Sustainable Communities (CSC-ATL)**

> An online GIS data portal that allows high school students, educators, community stakeholders, and research partners to visualize, analyze, and download air quality data from MAP-USA monitoring sites in the South Atlanta area.

---

## Quick Links

- **[Installation Guide](INSTALL.md)**
- **[Detailed Design Document](https://gtvault-my.sharepoint.com/:w:/g/personal/averma389_gatech_edu/IQDd2ieuyQbrRa0bizfsBXSuAT2qemHRFga7wBCoP2VgajU?e=cuPn1z)** 

---

## Release Notes - Version 1.0

*Released: April 28, 2025*

*Team Members: Riya Upadhyaya, Nithya Ravula, Amber Verma, Aditi Umapathy, Naperia Wilson*

---

### New Features in Version 1.0

This is the initial release of the Metro Atlanta Pollution Website. The following primary features were developed and delivered to the client:

#### Homepage
Users open the dashboard to an inviting homepage with a clean, light-green UI and a top navigation bar. Scrolling down reveals sections that communicate CSC-ATL's mission, purpose, and the significance of the pollution monitoring technology and this website to the South Atlanta community.

#### Educational Tab
The educational tab provides downloadable lesson modules formatted as PDFs alongside links to other relevant educational resources. Teachers can use these materials directly with their curriculum to educate students on the influence of air pollution in their communities. Interactive, clickable tabs and buttons unfold visually to explain the significance of pollution data. Brief module quizzes allow students to test their knowledge of the material.

#### Data Visualization Page
An embedded ArcGIS map is available with multiple data layers that can be clicked through representing different components of South Atlanta pollution. Users can download raw data in `.csv` format directly from the page.

#### About Us & Contact Page + Bug Report Form
An About Us page presents CSC-ATL's mission and background. A contact form allows any user to reach CSC-ATL directly by submitting their name, email, subject, and message, with a confirmation message shown upon successful submission. Users can report issues with the website through a dedicated "Report a Bug" form. The form accepts an issue title, description, and severity level. Submissions are routed to an admin view for review and resolution.

#### AI-Powered Pollution Analysis Chatbot *(Star Feature)*
A generative AI chatbot is integrated as a pop-up accessible on every page of the website. The chatbot is trained on South Atlanta pollution datasets and serves as an educational aide for students, teachers, and community members. Key capabilities include:

- **Educational material generation** - accepts a topic, grade level, and formatting preferences to generate pollution-focused educational content for copy or download.
- **Graph & visualization explanation** - accepts uploaded images of data visualizations (via file upload) and explains the data in the context of South Atlanta pollution.
- **ArcGIS map assistance** - answers user questions about the map's layers and the data they represent.
- **Educational module support** - clarifies air pollution concepts covered in the modules, helps users complete interactive activities, and provides hints or solutions for module quizzes.

---

### Bug Fixes in Version 1.0

The following bugs were identified and resolved during development:

- Resolved bug report form submission not successfully reaching the admin panel.
- Corrected chatbot memory retention issues.

---

### Known Bugs & Defects

There are no known bugs, but we do have some features that could be improved upon in the future or "defects":
- **Chatbot response latency** - On first load, the chatbot may take several seconds to respond while the AI model initializes. Subsequent responses are faster.
- **Module quiz score saving** - Quiz scores are not currently persisted between sessions (not stored in cache). Users who close or refresh the page will lose their progress.
- **Bug report admin panel notifications** - Real-time push notifications to admins for new bug submissions are not yet implemented; admins must manually check the admin panel.

*All promised functionality is included in the release*
