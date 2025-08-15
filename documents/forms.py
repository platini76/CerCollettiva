# documents/forms.py
from django import forms
from .models import Document

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['type', 'file', 'notes', 'data_classification', 'gdpr_consent']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'data_classification': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].widget.attrs.update({'class': 'form-select'})
        
        # Rendi il consenso GDPR obbligatorio per documenti con dati personali
        self.fields['gdpr_consent'].required = False
        
        # Aggiungi help text dinamico per il consenso GDPR
        self.fields['gdpr_consent'].help_text = """
            Confermo di aver letto l'informativa sulla privacy e acconsento al trattamento 
            dei dati personali contenuti in questo documento. I dati saranno utilizzati 
            esclusivamente per le finalità relative alla gestione della comunità energetica 
            e conservati secondo i termini di legge.
        """

    def clean(self):
        cleaned_data = super().clean()
        doc_type = cleaned_data.get('type')
        gdpr_consent = cleaned_data.get('gdpr_consent')
        data_classification = cleaned_data.get('data_classification')

        # Verifica consenso GDPR per documenti con dati personali
        if doc_type in ['ID_DOC', 'BILL'] or data_classification == 'PERSONAL':
            if not gdpr_consent:
                raise forms.ValidationError(
                    "Il consenso al trattamento dei dati è obbligatorio per questo tipo di documento"
                )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Verifica dimensione file (10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Il file non può superare i 10MB")
            
            # Verifica estensione file
            ext = file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise forms.ValidationError(
                    "Formato file non supportato. Utilizzare PDF, JPG o PNG"
                )
        return file