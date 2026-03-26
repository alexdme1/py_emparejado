import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Pairing from './pages/Pairing'
import Cropping from './pages/Cropping'
import VideoExtraction from './pages/VideoExtraction'
import Labeling from './pages/Labeling'
import Testing from './pages/Testing'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/pairing" element={<Pairing />} />
        <Route path="/cropping" element={<Cropping />} />
        <Route path="/video" element={<VideoExtraction />} />
        <Route path="/labeling" element={<Labeling />} />
        <Route path="/testing" element={<Testing />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

