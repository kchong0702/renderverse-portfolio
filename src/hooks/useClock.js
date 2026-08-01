import { useEffect, useState } from "react";

export const useClock = () => {
  const [time, setTime] = useState({
    hours: new Date().getHours().toString().padStart(2, "0"),
    minutes: new Date().getHours().toString().padStart(2, "0"),
  });

  useEffect(() => {
    const timer = setInterval(() => {
      const time = new Date();
      const hours = time.getHours().toString().padStart(2, "0");
      const minutes = time.getMinutes().toString().padStart(2, "0");
      setTime({ hours, minutes });
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, []);

  //   return `${hours}:${minutes}`;

  return time;
};
