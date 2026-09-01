document.getElementById('quizChapterModal').addEventListener('show.bs.modal', function()
{
    document.getElementById('quizChapterSubmit').click();
});

document.addEventListener("click", function (event) {
    const submitButton = event.target.closest("#submit-quiz");
    if (!submitButton) {
        return;
    }

    const quizItems = document.querySelectorAll("#serverResponseContent .quiz-item");
    let correctAnswers = 0;
    let unansweredQuestions = 0;

    quizItems.forEach(function (quizItem) {
        const selectedOption = quizItem.querySelector("input[type='radio']:checked");
        quizItem.classList.remove("text-success", "text-danger");

        if (!selectedOption) {
            unansweredQuestions += 1;
            quizItem.classList.add("text-danger");
        } else if (selectedOption.value === quizItem.dataset.correctAnswer) {
            correctAnswers += 1;
            quizItem.classList.add("text-success");
        } else {
            quizItem.classList.add("text-danger");
        }
    });

    const result = document.getElementById("quiz-result");
    if (result) {
        result.textContent = `You scored ${correctAnswers} out of ${quizItems.length}.`;
        if (unansweredQuestions > 0) {
            result.textContent += ` ${unansweredQuestions} question${unansweredQuestions === 1 ? "" : "s"} unanswered.`;
        }
    }
});

