import { FaRegCirclePlay } from "react-icons/fa6";
import Indicator from "../../ui/indicator/Indicator";

function GodzillaLPIndicator() {
  return (
    <>
      <Indicator
        settings={{
          position: [0, 1.4, 0],
          rotation: [0, 0, 0],
          icon: <FaRegCirclePlay size={25} />,
          id: "animateindicator",
        }}
      />
    </>
  );
}

export default GodzillaLPIndicator;
