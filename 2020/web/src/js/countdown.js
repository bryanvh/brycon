function calculateTimeRemaining(timerEnd) {
  var timeDiff = Date.parse(timerEnd) - Date.parse(new Date());
  
  var secondsLeft = Math.floor((timeDiff / 1000) % 60);
  var minutesLeft = Math.floor((timeDiff / 1000 / 60) % 60);
  var hoursLeft = Math.floor((timeDiff / (1000 * 60 * 60)) % 24);
  var daysLeft = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
  
  return {
     'total': timeDiff,
     'days': daysLeft,
     'hours': hoursLeft,
     'minutes': minutesLeft,
     'seconds': secondsLeft
   };
}

function initCountdown(displayId, timerEnd) {
  var display = document.getElementById(displayId);
  var timerInterval = setInterval(function() {
    var timer = calculateTimeRemaining(timerEnd);
    if(timer.total > 0) {
      display.innerHTML = timer.days + " days, " + timer.hours + " hours, " + timer.minutes + " mins, " + timer.seconds + " secs";
    } else if(timer.days > -1 && timer.days <= 0) {
      display.innerHTML = "It's game time!";
      clearInterval(timerInterval);
    } else {
      display.innerHTML = "Thanks for playing! See you in 2020!"
      clearInterval(timerInterval);
    }
  }, 1000);
}