import { Link } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="Pagina non trovata" description="L'indirizzo richiesto non corrisponde a nessuna sezione di NEXUS." />
      <Link to="/" className="text-sm text-gold-300 hover:underline">Torna alla dashboard</Link>
    </>
  );
}
