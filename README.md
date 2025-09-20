1. 🌍 Purpose of the Project

To make municipal complaint submission simple, accurate, and transparent.

To help authorities prioritize and resolve issues faster.

To reduce manual workload and improve trust between citizens and government.

2. 🛑 Problems in Existing System

Manual complaint filing through phone calls, emails, or office visits.

Confusing interfaces and unclear categories.

Misclassification of complaints leading to delays.

No transparency in tracking complaint status.

Authorities waste time manually sorting complaints.

3. 💡 Proposed Solution (This Project)

A web platform where citizens can easily submit complaints.

Random Forest ML model automatically categorizes complaints (e.g., water, garbage, road).

MongoDB database securely stores complaint details and status.

Voting system lets citizens support existing complaints to highlight urgent issues.

Citizens can track complaint status in real-time, ensuring transparency.

4. 🛠️ How the System Works (Workflow)

Complaint Submission – User enters issue through React frontend.

Backend Processing – Flask backend receives complaint.

Classification – Random Forest model predicts category.

Data Storage – Complaint details saved in MongoDB.

User Interaction – Citizens can vote and track complaint status.

Authority Dashboard – Officials can view, prioritize, and resolve issues.

5. 🚀 Key Benefits

Saves time and effort for both citizens and authorities.

Ensures accuracy in categorization.

Brings transparency with status tracking.

Engages citizens through voting and participation.

Scalable and easy to extend with more features (voice input, multilingual, etc.).

Example overflow

User → React Frontend → Flask API → Random Forest Model → MongoDB → Response → User

Backend:
cd Final\Final
& venv\Scripts\Activate.ps1
python rf.py

Frontend:
cd Final\Final\complaint
npm start


